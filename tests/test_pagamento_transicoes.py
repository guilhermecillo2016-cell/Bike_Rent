"""
tests/test_pagamento_transicoes.py
------------------------------------
Statechart do Pagamento ([C12]):

    PENDENTE --aprovar()--> APROVADO
    PENDENTE --recusar()--> RECUSADO
    PENDENTE --cancelar()--> CANCELADO   (PIX vencido: verificar_status_pix)

APROVADO, RECUSADO e CANCELADO são estados finais: qualquer transição a partir
deles levanta ConflitoDeRegra (409).
"""

from datetime import datetime, timedelta

import pytest

from dominio.erros import ConflitoDeRegra
from dominio.pagamento.metodos_pagamento import PagamentoPix
from dominio.pagamento.pagamento import Pagamento
from servicos_tecnicos.banco_de_dados.enums import StatusPagamento, TipoPagamento
from tests.test_metodos_pagamento import GatewayFalso, novo_servico

AGORA = datetime(2026, 11, 18, 12, 0, 0)
PENDENTE = StatusPagamento.PENDENTE
APROVADO = StatusPagamento.APROVADO
RECUSADO = StatusPagamento.RECUSADO
CANCELADO = StatusPagamento.CANCELADO
PIX = TipoPagamento.PIX
CREDITO = TipoPagamento.CARTAO_CREDITO
DEBITO = TipoPagamento.CARTAO_DEBITO
EMAIL = "ana@exemplo.com"


def pagamento(tipo=CREDITO, expira_em=None, status=PENDENTE):
    p = Pagamento(20.0, tipo, expira_em=expira_em)
    p.status = status
    return p


# --- enum e estado inicial --------------------------------------------
def test_status_pagamento_tem_os_quatro_estados():
    assert [s.value for s in StatusPagamento] == ["PENDENTE", "APROVADO", "RECUSADO", "CANCELADO"]
    assert StatusPagamento.CANCELADO == "CANCELADO"


def test_nasce_pendente_e_sem_validade():
    p = Pagamento(20.0, CREDITO)
    assert p.status == PENDENTE
    assert p.expira_em is None


def test_expira_em_e_guardado():
    validade = AGORA + timedelta(minutes=15)
    assert Pagamento(20.0, PIX, expira_em=validade).expira_em == validade


# --- a partir de PENDENTE -------------------------------------------
@pytest.mark.parametrize(
    "metodo, destino",
    [("aprovar", APROVADO), ("recusar", RECUSADO), ("cancelar", CANCELADO)],
)
def test_pendente_vai_para_o_destino_da_transicao(metodo, destino):
    p = pagamento()
    getattr(p, metodo)()
    assert p.status == destino


# --- estados finais: toda transição é erro -------------------------------
@pytest.mark.parametrize("final", [APROVADO, RECUSADO, CANCELADO])
@pytest.mark.parametrize("metodo", ["aprovar", "recusar", "cancelar"])
def test_estado_final_nao_aceita_transicao(final, metodo):
    p = pagamento(status=final)
    with pytest.raises(ConflitoDeRegra) as erro:
        getattr(p, metodo)()
    assert erro.value.status_code == 409
    assert p.status == final  # nada mudou


def test_so_se_sai_de_pendente_uma_vez():
    p = pagamento()
    p.aprovar()
    with pytest.raises(ConflitoDeRegra):
        p.recusar()
    assert p.status == APROVADO


# --- verificar_status_pix ------------------------------------------------
def test_pix_pendente_vencido_e_cancelado():
    p = pagamento(PIX, expira_em=AGORA - timedelta(seconds=1))
    assert p.verificar_status_pix(AGORA) == CANCELADO
    assert p.status == CANCELADO


def test_pix_que_vence_exatamente_agora_e_cancelado():
    p = pagamento(PIX, expira_em=AGORA)
    assert p.verificar_status_pix(AGORA) == CANCELADO


def test_pix_pendente_dentro_da_validade_continua_pendente():
    p = pagamento(PIX, expira_em=AGORA + timedelta(seconds=1))
    assert p.verificar_status_pix(AGORA) == PENDENTE
    assert p.status == PENDENTE


def test_pix_sem_validade_continua_pendente():
    p = pagamento(PIX, expira_em=None)
    assert p.verificar_status_pix(AGORA) == PENDENTE


@pytest.mark.parametrize("final", [APROVADO, RECUSADO, CANCELADO])
def test_pix_que_ja_saiu_de_pendente_devolve_o_status_sem_erro(final):
    p = pagamento(PIX, expira_em=AGORA - timedelta(hours=1), status=final)
    assert p.verificar_status_pix(AGORA) == final
    assert p.status == final


@pytest.mark.parametrize("tipo", [CREDITO, DEBITO])
def test_pagamento_que_nao_e_pix_nunca_e_cancelado_por_validade(tipo):
    p = pagamento(tipo, expira_em=AGORA - timedelta(hours=1))
    assert p.verificar_status_pix(AGORA) == PENDENTE
    assert p.status == PENDENTE


def test_verificar_varias_vezes_e_seguro():
    p = pagamento(PIX, expira_em=AGORA - timedelta(minutes=1))
    assert p.verificar_status_pix(AGORA) == CANCELADO
    assert p.verificar_status_pix(AGORA) == CANCELADO  # já cancelado: sem erro


# --- o service usa as transições, não atribui status ------------------------
@pytest.mark.parametrize(
    "resposta, metodo, esperado",
    [
        (APROVADO, "aprovar", APROVADO),
        (RECUSADO, "recusar", RECUSADO),
    ],
)
def test_cartao_pelo_service_passa_pelos_metodos_de_transicao(monkeypatch, resposta, metodo, esperado):
    chamadas = []
    original = getattr(Pagamento, metodo)

    def espiao(self):
        chamadas.append(metodo)
        original(self)

    monkeypatch.setattr(Pagamento, metodo, espiao)
    service = novo_servico(GatewayFalso(resposta))

    resultado = service.cobrar_corrida(EMAIL, 18.0, locacao_id=10)

    assert chamadas == [metodo]
    assert resultado.status == esperado


def test_service_nao_atribui_status_direto(monkeypatch):
    # Se o service atribuísse status, o pagamento sairia de PENDENTE sem passar
    # por aprovar(): com aprovar() neutralizado ele tem que continuar PENDENTE.
    monkeypatch.setattr(Pagamento, "aprovar", lambda self: None)
    service = novo_servico(GatewayFalso(APROVADO))

    resultado = service.cobrar_corrida(EMAIL, 18.0, locacao_id=10)

    assert resultado.status == PENDENTE


def test_pix_pelo_service_fica_pendente_com_validade():
    service = novo_servico(credito=None, debito=None)
    service.metodos[PIX] = PagamentoPix(validade_minutos=15, relogio=lambda: AGORA)

    resultado = service.cobrar_pacote(EMAIL, 27.0, pacote_id=7, tipo=PIX)

    assert resultado.status == PENDENTE
    assert resultado.expira_em == AGORA + timedelta(minutes=15)
    assert resultado.verificar_status_pix(AGORA) == PENDENTE
    assert resultado.verificar_status_pix(AGORA + timedelta(minutes=16)) == CANCELADO


def test_pix_processar_define_a_validade_do_pagamento():
    pix = PagamentoPix(validade_minutos=10, relogio=lambda: AGORA)
    p = Pagamento(30.0, PIX)
    assert pix.processar(p, usuario=None) == PENDENTE
    assert p.expira_em == AGORA + timedelta(minutes=10)
