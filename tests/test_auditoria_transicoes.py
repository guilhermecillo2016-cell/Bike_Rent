"""
tests/test_auditoria_transicoes.py
------------------------------------
[A26] Statechart da Bicicleta: "Cada troca de estado gera um EventoAuditoria".

Cada transição do statechart gera exatamente um evento (BICICLETA, status
anterior, status novo, quem causou). Operação recusada ou que não muda o
status não gera evento.
"""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from dominio.auditoria import service as auditoria
from dominio.avaria import service as avaria_service
from dominio.bicicleta import service as bicicleta_service
from dominio.bicicleta.schemas import BicicletaCreate
from dominio.estacao import service as estacao_service
from dominio.estacao.schemas import EstacaoCreate
from dominio.locacao import service as locacao_service
from dominio.pagamento import service as pagamento_service
from dominio.pagamento.schemas import CartaoCreate
from dominio.relatorio import service as relatorio_service
from dominio.usuario.usuario import Usuario
from servicos_tecnicos.banco_de_dados import memoria
from servicos_tecnicos.banco_de_dados.enums import StatusBicicleta, StatusPagamento
from servicos_tecnicos.iot import definir_trava
from servicos_tecnicos.iot.mock import ModoTrava, TravaInteligenteMock

DISPONIVEL = StatusBicicleta.DISPONIVEL
EM_USO = StatusBicicleta.EM_USO
EM_MANUTENCAO = StatusBicicleta.EM_MANUTENCAO
BLOQUEADA = StatusBicicleta.BLOQUEADA

CICLISTA = "cid@x.com"
OP = "op@x.com"


@pytest.fixture(autouse=True)
def _limpa(monkeypatch):
    colecoes = (
        memoria.estacoes, memoria.bicicletas, memoria.locacoes, memoria.cartoes,
        memoria.pacotes, memoria.avarias, memoria.eventos_auditoria, memoria.usuarios,
        memoria.pagamentos, memoria.comprovantes,
    )
    for c in colecoes:
        c.clear()
    memoria._contadores.clear()
    memoria.usuarios[CICLISTA] = Usuario("Cid", CICLISTA)
    definir_trava(TravaInteligenteMock(ModoTrava.SUCESSO))
    monkeypatch.setattr(
        pagamento_service.PagamentoService, "cobrar_corrida",
        lambda self, email, valor, locacao_id: SimpleNamespace(status=StatusPagamento.APROVADO),
    )
    yield
    definir_trava(None)
    for c in colecoes:
        c.clear()


def _estacao(nome="E", lat=0.0):
    return estacao_service.criar_estacao(
        EstacaoCreate(nome=nome, endereco="Rua", latitude=lat, longitude=0, capacidade_total=10)
    )


def _bicicleta(status=DISPONIVEL):
    """Bicicleta já no `status` pedido, sem nenhum evento contado."""
    bicicleta = bicicleta_service.cadastrar_bicicleta(BicicletaCreate(estacao_id=_estacao().id))
    if status == EM_USO:
        estacao_service.remover_bicicleta(bicicleta.id)
    if status != DISPONIVEL:
        bicicleta_service.set_status(bicicleta.id, status)
    memoria.eventos_auditoria.clear()
    return bicicleta


def _eventos():
    """(quem, anterior, novo) do mais antigo para o mais recente."""
    return [
        (e.usuario_email, e.status_anterior, e.status_novo)
        for e in reversed(auditoria.listar())
        if e.tipo_entidade == "BICICLETA"
    ]


def _sem_avaria():
    return False


# --- Corrida ------------------------------------------------------------
def test_iniciar_uso_disponivel_para_em_uso_gera_evento_do_ciclista():
    b = _bicicleta(DISPONIVEL)
    bicicleta_service.iniciar_uso(b, CICLISTA)
    assert b.status == EM_USO
    assert _eventos() == [(CICLISTA, "DISPONIVEL", "EM_USO")]


def test_finalizar_uso_sem_bloqueio_em_uso_para_disponivel_gera_evento():
    b = _bicicleta(EM_USO)
    bicicleta_service.finalizar_uso(b.id, CICLISTA)
    assert b.status == DISPONIVEL
    assert _eventos() == [(CICLISTA, "EM_USO", "DISPONIVEL")]


def test_finalizar_uso_com_bloqueio_em_uso_para_em_manutencao_gera_evento():
    b = _bicicleta(EM_USO)
    b.bloqueio_pendente = True
    bicicleta_service.finalizar_uso(b.id, CICLISTA)
    assert b.status == EM_MANUTENCAO and b.bloqueio_pendente is False
    assert _eventos() == [(CICLISTA, "EM_USO", "EM_MANUTENCAO")]


def test_corrida_completa_gera_exatamente_dois_eventos():
    origem, destino = _estacao("Origem"), _estacao("Destino", lat=0.01)
    b = bicicleta_service.cadastrar_bicicleta(BicicletaCreate(estacao_id=origem.id))
    pagamento_service.vincular_cartao(
        CICLISTA,
        CartaoCreate(numero_cartao="4111111111111111", nome_titular="Cid",
                     validade="12/99", cvv="123"),
    )

    locacao_service.iniciar_locacao(CICLISTA, b.qr_code)
    locacao_service.encerrar_locacao(CICLISTA, destino.id)

    assert b.status == DISPONIVEL
    assert _eventos() == [
        (CICLISTA, "DISPONIVEL", "EM_USO"),
        (CICLISTA, "EM_USO", "DISPONIVEL"),
    ]


def test_corrida_com_avaria_reportada_gera_tres_eventos():
    origem, destino = _estacao("Origem"), _estacao("Destino", lat=0.01)
    b = bicicleta_service.cadastrar_bicicleta(BicicletaCreate(estacao_id=origem.id))
    pagamento_service.vincular_cartao(
        CICLISTA,
        CartaoCreate(numero_cartao="4111111111111111", nome_titular="Cid",
                     validade="12/99", cvv="123"),
    )

    locacao_service.iniciar_locacao(CICLISTA, b.qr_code)
    locacao_service.encerrar_locacao(CICLISTA, destino.id, descricao_avaria="Pneu furado")

    assert b.status == EM_MANUTENCAO
    assert _eventos() == [
        (CICLISTA, "DISPONIVEL", "EM_USO"),
        (CICLISTA, "EM_USO", "DISPONIVEL"),
        (CICLISTA, "DISPONIVEL", "EM_MANUTENCAO"),
    ]


# --- Troca manual e manutenção (um evento por transição) ----------------
@pytest.mark.parametrize(
    "origem, pedido",
    [
        (DISPONIVEL, EM_MANUTENCAO),
        (DISPONIVEL, BLOQUEADA),
        (EM_MANUTENCAO, DISPONIVEL),
        (EM_MANUTENCAO, BLOQUEADA),
        (BLOQUEADA, DISPONIVEL),
        (BLOQUEADA, EM_MANUTENCAO),
    ],
)
def test_troca_manual_gera_um_evento_do_operador(origem, pedido):
    b = _bicicleta(origem)
    bicicleta_service.alterar_status_manual(b.id, pedido, OP)
    assert b.status == pedido
    assert _eventos() == [(OP, str(origem), str(pedido))]


def test_troca_manual_em_uso_agenda_o_bloqueio_com_um_evento():
    b = _bicicleta(EM_USO)
    bicicleta_service.alterar_status_manual(b.id, BLOQUEADA, OP)
    assert b.status == EM_USO and b.bloqueio_pendente is True
    assert _eventos() == [(OP, "EM_USO", "EM_MANUTENCAO (agendado)")]


@pytest.mark.parametrize("origem", [DISPONIVEL, EM_USO, BLOQUEADA])
def test_enviar_para_manutencao_por_avaria_gera_um_evento(origem):
    b = _bicicleta(origem)
    avaria_service.reportar_avaria(CICLISTA, b.id, "Freio")
    assert b.status == EM_MANUTENCAO
    assert _eventos() == [(CICLISTA, str(origem), "EM_MANUTENCAO")]


def test_liberar_apos_reparo_gera_um_evento():
    b = _bicicleta(DISPONIVEL)
    avaria = avaria_service.reportar_avaria(CICLISTA, b.id, "Freio")
    memoria.eventos_auditoria.clear()
    avaria_service.resolver_avaria(avaria.id, OP)
    assert b.status == DISPONIVEL
    assert _eventos() == [(OP, "EM_MANUTENCAO", "DISPONIVEL")]


def test_set_status_gera_evento_quando_muda():
    b = _bicicleta(DISPONIVEL)
    bicicleta_service.set_status(b.id, BLOQUEADA)
    assert _eventos() == [("sistema", "DISPONIVEL", "BLOQUEADA")]


# --- Sem mudança de status, sem evento ----------------------------------
def _codigo(funcao, *args):
    with pytest.raises(HTTPException) as erro:
        funcao(*args)
    return erro.value.status_code


@pytest.mark.parametrize("origem", [EM_USO, EM_MANUTENCAO, BLOQUEADA])
def test_iniciar_uso_recusado_nao_gera_evento(origem):
    b = _bicicleta(origem)
    assert _codigo(bicicleta_service.iniciar_uso, b, CICLISTA) == 409
    assert _eventos() == []


@pytest.mark.parametrize("origem", [DISPONIVEL, EM_MANUTENCAO, BLOQUEADA])
def test_finalizar_uso_recusado_nao_gera_evento(origem):
    b = _bicicleta(origem)
    assert _codigo(bicicleta_service.finalizar_uso, b.id, CICLISTA) == 409
    assert _eventos() == []


def test_liberar_bicicleta_em_uso_recusado_nao_gera_evento():
    b = _bicicleta(EM_USO)
    assert _codigo(bicicleta_service.alterar_status_manual, b.id, DISPONIVEL, OP) == 409
    assert _eventos() == []


def test_liberar_com_avaria_pendente_recusado_nao_gera_evento():
    b = _bicicleta(DISPONIVEL)
    avaria_service.reportar_avaria(CICLISTA, b.id, "Freio")
    memoria.eventos_auditoria.clear()
    assert _codigo(bicicleta_service.alterar_status_manual, b.id, DISPONIVEL, OP) == 409
    assert _eventos() == []


@pytest.mark.parametrize("status", [DISPONIVEL, EM_MANUTENCAO, BLOQUEADA])
def test_mesmo_status_nao_gera_evento(status):
    b = _bicicleta(status)
    bicicleta_service.alterar_status_manual(b.id, status, OP)
    bicicleta_service.set_status(b.id, status)
    assert _eventos() == []


def test_avaria_em_bicicleta_ja_em_manutencao_nao_gera_evento():
    b = _bicicleta(EM_MANUTENCAO)
    avaria_service.reportar_avaria(CICLISTA, b.id, "Freio")
    assert b.status == EM_MANUTENCAO
    assert _eventos() == []


# --- Os eventos novos não mudam o relatório -----------------------------
def test_relatorio_nao_depende_dos_eventos_de_auditoria():
    origem, destino = _estacao("Origem"), _estacao("Destino", lat=0.01)
    b = bicicleta_service.cadastrar_bicicleta(BicicletaCreate(estacao_id=origem.id))
    pagamento_service.vincular_cartao(
        CICLISTA,
        CartaoCreate(numero_cartao="4111111111111111", nome_titular="Cid",
                     validade="12/99", cvv="123"),
    )
    locacao_service.iniciar_locacao(CICLISTA, b.qr_code)
    locacao_service.encerrar_locacao(CICLISTA, destino.id)

    com_eventos = relatorio_service.gerar_relatorio().model_dump(exclude={"data_geracao"})
    memoria.eventos_auditoria.clear()
    sem_eventos = relatorio_service.gerar_relatorio().model_dump(exclude={"data_geracao"})

    assert com_eventos == sem_eventos
