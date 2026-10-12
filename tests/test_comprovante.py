from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException

from dominio.bicicleta import service as bicicleta_service
from dominio.bicicleta.schemas import BicicletaCreate
from dominio.comprovante import service as comprovante_service
from dominio.estacao import service as estacao_service
from dominio.estacao.schemas import EstacaoCreate
from dominio.locacao import service as locacao_service
from dominio.pagamento import service as pagamento_service
from dominio.pagamento.schemas import CartaoCreate
from servicos_tecnicos.banco_de_dados import memoria, repository_pacote
from servicos_tecnicos.iot import definir_trava
from servicos_tecnicos.iot.mock import ModoTrava, TravaInteligenteMock

EMAIL = "c@x.com"
OUTRO = "outro@x.com"
NUMERO = "4111111111111111"


@pytest.fixture(autouse=True)
def _limpa():
    for d in (memoria.estacoes, memoria.bicicletas, memoria.locacoes, memoria.cartoes,
              memoria.pacotes, memoria.pagamentos, memoria.comprovantes):
        d.clear()
    definir_trava(TravaInteligenteMock(ModoTrava.SUCESSO))
    yield
    definir_trava(None)


def _estacao(nome, lat=0.0):
    return estacao_service.criar_estacao(
        EstacaoCreate(nome=nome, endereco="Rua", latitude=lat, longitude=0, capacidade_total=10)
    )


def _encerrar(segundos=120, pacote_min=0):
    origem, destino = _estacao("Origem"), _estacao("Destino", 0.01)
    bike = bicicleta_service.cadastrar_bicicleta(BicicletaCreate(estacao_id=origem.id))
    pagamento_service.vincular_cartao(
        EMAIL,
        CartaoCreate(numero_cartao=NUMERO, nome_titular="Fulano",
                     validade="12/99", cvv="123", tipo="credito"),
    )
    loc = locacao_service.iniciar_locacao(EMAIL, bike.qr_code)
    loc.data_hora_inicio = datetime.now() - timedelta(seconds=segundos)
    if pacote_min:
        p = repository_pacote.create(EMAIL, pacote_min, datetime.now() + timedelta(days=7))
        p.ativo = True
    r = locacao_service.encerrar_locacao(EMAIL, destino.id)
    return loc, r


def test_comprovante_gerado_ao_encerrar():
    loc, r = _encerrar(120)
    c = comprovante_service.obter_do_ciclista(loc.id, EMAIL)
    assert r.comprovante_id == c.id
    assert c.trajeto == "Origem → Destino"
    assert c.duracao_minutos == 2
    assert c.tarifa_aplicada == loc.valor_total
    assert c.pago_com_pacote is False
    assert "final 1111" in c.metodo_pagamento


def test_pacote_cobriu_tudo_sem_pagamento():
    loc, _ = _encerrar(120, pacote_min=30)
    c = comprovante_service.obter_do_ciclista(loc.id, EMAIL)
    assert c.pago_com_pacote is True and c.pagamento_status is None
    assert c.metodo_pagamento == "Pago com pacote de minutos"
    assert c.minutos_pacote == 2


def test_pacote_parcial_mostra_pacote_e_cartao():
    loc, _ = _encerrar(8 * 60 - 30, pacote_min=5)
    c = comprovante_service.obter_do_ciclista(loc.id, EMAIL)
    assert c.metodo_pagamento.startswith("Pacote de minutos + ")
    assert "final 1111" in c.metodo_pagamento


def test_outro_ciclista_recebe_404():
    loc, _ = _encerrar()
    with pytest.raises(HTTPException) as e:
        comprovante_service.obter_do_ciclista(loc.id, OUTRO)
    assert e.value.status_code == 404


def test_locacao_inexistente_404():
    with pytest.raises(HTTPException) as e:
        comprovante_service.obter_do_ciclista(999, EMAIL)
    assert e.value.status_code == 404


def test_nunca_expoe_numero_completo():
    loc, _ = _encerrar()
    corpo = comprovante_service.obter_do_ciclista(loc.id, EMAIL).model_dump_json()
    assert NUMERO not in corpo and "123" not in corpo.replace("1111", "")