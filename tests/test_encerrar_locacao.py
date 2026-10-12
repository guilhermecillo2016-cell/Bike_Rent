from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from dominio.bicicleta import service as bicicleta_service
from dominio.bicicleta.schemas import BicicletaCreate
from dominio.estacao import service as estacao_service
from dominio.estacao.schemas import EstacaoCreate
from dominio.locacao import service as locacao_service, tarifa
from dominio.pagamento import service as pagamento_service
from dominio.pagamento.schemas import CartaoCreate
from servicos_tecnicos.banco_de_dados import memoria, repository_pacote
from servicos_tecnicos.banco_de_dados.enums import (
    StatusBicicleta, StatusEstacao, StatusPagamento,
)
from servicos_tecnicos.iot import definir_trava
from servicos_tecnicos.iot.mock import ModoTrava, TravaInteligenteMock

EMAIL = "c@x.com"


@pytest.fixture(autouse=True)
def _limpa():
    for d in (memoria.estacoes, memoria.bicicletas, memoria.locacoes,
              memoria.cartoes, memoria.pacotes, memoria.eventos_auditoria):
        d.clear()
    definir_trava(TravaInteligenteMock(ModoTrava.SUCESSO))
    yield
    definir_trava(None)

class _Cobrancas(list):
    """Lista de valores cobrados + status que o falso devolve."""
    status = StatusPagamento.APROVADO


@pytest.fixture
def cobrancas(monkeypatch):
    """Substitui a cobrança real; a lista guarda os valores cobrados e
    `cobrancas.status` define o que o gateway falso devolve."""
    chamadas = _Cobrancas()

    def falso(self, email, valor, locacao_id):
        chamadas.append(valor)
        return SimpleNamespace(status=chamadas.status)

    monkeypatch.setattr(pagamento_service.PagamentoService, "cobrar_corrida", falso)
    return chamadas



def _estacao(nome="E", capacidade=10, lat=0.0, lon=0.0):
    return estacao_service.criar_estacao(
        EstacaoCreate(nome=nome, endereco="Rua", latitude=lat, longitude=lon,
                      capacidade_total=capacidade)
    )


def _corrida(segundos=120):
    """Origem + destino, corrida iniciada há `segundos`. Devolve (origem, destino, bike, loc)."""
    origem, destino = _estacao("Origem"), _estacao("Destino", lat=0.01)
    bike = bicicleta_service.cadastrar_bicicleta(BicicletaCreate(estacao_id=origem.id))
    pagamento_service.vincular_cartao(
        EMAIL,
        CartaoCreate(numero_cartao="4111111111111111", nome_titular="Fulano",
                     validade="12/99", cvv="123"),
    )
    loc = locacao_service.iniciar_locacao(EMAIL, bike.qr_code)
    loc.data_hora_inicio = datetime.now() - timedelta(seconds=segundos)
    return origem, destino, bike, loc


def _pacote(minutos):
    p = repository_pacote.create(EMAIL, minutos, datetime.now() + timedelta(days=7))
    p.ativo = True
    return p


def test_sucesso_devolve_bike_e_atualiza_vagas(cobrancas):
    origem, destino, bike, loc = _corrida(120)  # 2 min
    r = locacao_service.encerrar_locacao(EMAIL, destino.id)

    assert bike.status == StatusBicicleta.DISPONIVEL
    assert bike.estacao_id == destino.id
    assert estacao_service.vagas_disponiveis(origem) == 10
    assert estacao_service.vagas_disponiveis(destino) == 9
    assert loc.em_andamento is False
    assert loc.estacao_destino_id == destino.id and loc.data_hora_fim is not None
    assert r.duracao_minutos == 2
    assert r.valor_total == tarifa.calcular_valor(2)
    assert cobrancas == [tarifa.calcular_valor(2)]
    assert r.cobranca_pendente is False


def test_sem_corrida_ativa_404():
    destino = _estacao()
    with pytest.raises(HTTPException) as e:
        locacao_service.encerrar_locacao(EMAIL, destino.id)
    assert e.value.status_code == 404


def test_destino_lotada_sugere_proximas_e_nao_toca_na_trava(cobrancas):
    trava = TravaInteligenteMock(ModoTrava.SUCESSO)
    _, _, bike, loc = _corrida()
    definir_trava(trava)
    cheia = _estacao("Cheia", capacidade=1, lat=0.02)
    bicicleta_service.cadastrar_bicicleta(BicicletaCreate(estacao_id=cheia.id))
    livre = _estacao("Livre", lat=0.03)

    with pytest.raises(locacao_service.EstacaoDestinoIndisponivel) as e:
        locacao_service.encerrar_locacao(EMAIL, cheia.id)

    assert livre.id in [s.id for s in e.value.sugestoes]
    assert cheia.id not in [s.id for s in e.value.sugestoes]
    assert trava.travas == []
    assert loc.em_andamento is True and bike.status == StatusBicicleta.EM_USO


def test_destino_bloqueada(cobrancas):
    _, destino, bike, loc = _corrida()
    estacao_service.alterar_status_manual(destino.id, StatusEstacao.BLOQUEADA, "adm@x.com")
    with pytest.raises(locacao_service.EstacaoDestinoIndisponivel):
        locacao_service.encerrar_locacao(EMAIL, destino.id)
    assert loc.em_andamento is True


@pytest.mark.parametrize("modo", [ModoTrava.TIMEOUT, ModoTrava.FALHA])
def test_travamento_nao_confirmado_mantem_corrida(modo, cobrancas):
    _, destino, bike, loc = _corrida()
    definir_trava(TravaInteligenteMock(modo))
    with pytest.raises(HTTPException) as e:
        locacao_service.encerrar_locacao(EMAIL, destino.id)
    assert e.value.status_code == 503
    assert loc.em_andamento is True
    assert bike.status == StatusBicicleta.EM_USO and bike.estacao_id is None
    assert cobrancas == []


def test_pacote_abate_parte_e_cobra_excedente(cobrancas):
    _, destino, _, loc = _corrida(8 * 60 - 30)  # 8 min iniciados
    pacote = _pacote(5)
    r = locacao_service.encerrar_locacao(EMAIL, destino.id)
    assert r.minutos_pacote == 5
    assert r.valor_total == tarifa.calcular_valor(3)
    assert cobrancas == [tarifa.calcular_valor(3)]
    assert pacote.minutos_restantes == 0 and pacote.ativo is False


def test_pacote_cobre_tudo_nao_cobra(cobrancas):
    _, destino, _, loc = _corrida(120)
    _pacote(30)
    r = locacao_service.encerrar_locacao(EMAIL, destino.id)
    assert r.valor_total == 0.0
    assert cobrancas == []
    assert r.pagamento_status is None and r.cobranca_pendente is False


def test_bloqueio_pendente_manda_para_manutencao(cobrancas):
    _, destino, bike, _ = _corrida()
    bicicleta_service.alterar_status_manual(bike.id, StatusBicicleta.EM_MANUTENCAO, "adm@x.com")
    assert bike.bloqueio_pendente is True
    r = locacao_service.encerrar_locacao(EMAIL, destino.id)
    assert bike.status == StatusBicicleta.EM_MANUTENCAO
    assert bike.bloqueio_pendente is False
    assert r.bicicleta_em_manutencao is True
    assert bike.estacao_id == destino.id  # fica fisicamente na estação


def test_cobranca_recusada_fecha_corrida_mesmo_assim(cobrancas):
    cobrancas.status = StatusPagamento.RECUSADO  
    _, destino, _, loc = _corrida(120)
    r = locacao_service.encerrar_locacao(EMAIL, destino.id)
    assert loc.em_andamento is False
    assert r.pagamento_status == StatusPagamento.RECUSADO
    assert r.cobranca_pendente is True