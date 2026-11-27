"""
tests/test_metodos_pagamento.py
---------------------------------
Padrão Strategy do pagamento ([C11]): MetodoPagamento e as estratégias
PagamentoCartaoCredito, PagamentoCartaoDebito e PagamentoPix, mais a escolha da
estratégia no PagamentoService (dicionário TipoPagamento -> MetodoPagamento).
Todos os testes usam gateway falso.
"""

import ast
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from dominio.pagamento import metodos_pagamento
from dominio.pagamento.metodos_pagamento import (
    MetodoPagamento,
    PagamentoCartaoCredito,
    PagamentoCartaoDebito,
    PagamentoPix,
)
from dominio.pagamento.pagamento import Pagamento
from dominio.pagamento.service import PagamentoService
from servicos_tecnicos.banco_de_dados.enums import StatusPagamento, TipoPagamento
from servicos_tecnicos.pagamentos.gateway import TOKEN_CARTAO_RECUSADO

EMAIL = "ana@exemplo.com"
CREDITO = TipoPagamento.CARTAO_CREDITO
DEBITO = TipoPagamento.CARTAO_DEBITO
PIX = TipoPagamento.PIX


# --- Fakes ------------------------------------------------------------
class GatewayFalso:
    def __init__(self, resultado=StatusPagamento.APROVADO):
        self.resultado = resultado
        self.chamadas = []

    def cobrar(self, token, valor):
        self.chamadas.append((token, valor))
        return self.resultado


class FakePagamentoRepo:
    def __init__(self):
        self.itens = {}

    def create(self, valor, tipo, locacao=None, pacote=None, token_cartao=None):
        pagamento = Pagamento(
            valor, tipo, locacao=locacao, pacote=pacote, token_cartao=token_cartao,
            id_pagamento=len(self.itens) + 1,
        )
        self.itens[pagamento.id] = pagamento
        return pagamento

    def get_by_id(self, pagamento_id):
        return self.itens.get(pagamento_id)

    def list_all(self):
        return list(self.itens.values())


class FakeCartaoRepo:
    def __init__(self, credito=None, debito=None):
        self._credito, self._debito = credito, debito

    def get_credito_by_email(self, email):
        return self._credito

    def get_debito_by_email(self, email):
        return self._debito


class FakeIdRepo:
    """Devolve um objeto com o id pedido (serve para locação e pacote)."""

    def __init__(self, campo):
        self.campo = campo

    def get_by_id(self, id_):
        return SimpleNamespace(**{self.campo: id_})


def cartao(token):
    return SimpleNamespace(token=token)


def novo_servico(gateway=None, credito="tok_credito", debito="tok_debito", usuario_repo=None):
    return PagamentoService(
        pagamento_repo=FakePagamentoRepo(),
        cartao_repo=FakeCartaoRepo(
            credito=cartao(credito) if credito else None,
            debito=cartao(debito) if debito else None,
        ),
        locacao_repo=FakeIdRepo("id_locacao"),
        pacote_repo=FakeIdRepo("id_pacote"),
        gateway=gateway or GatewayFalso(),
        usuario_repo=usuario_repo or SimpleNamespace(get_by_email=lambda email: None),
    )


# --- Interface --------------------------------------------------------
def test_metodo_pagamento_e_uma_interface_abstrata():
    with pytest.raises(TypeError):
        MetodoPagamento()


@pytest.mark.parametrize(
    "estrategia, tipo",
    [
        (PagamentoCartaoCredito(GatewayFalso()), CREDITO),
        (PagamentoCartaoDebito(GatewayFalso()), DEBITO),
        (PagamentoPix(), PIX),
    ],
)
def test_cada_estrategia_atende_um_tipo(estrategia, tipo):
    assert isinstance(estrategia, MetodoPagamento)
    assert estrategia.tipo == tipo


def test_o_modulo_nao_importa_infraestrutura():
    fonte = Path(metodos_pagamento.__file__).read_text(encoding="utf-8")
    importados = set()
    for no in ast.walk(ast.parse(fonte)):
        if isinstance(no, ast.Import):
            importados |= {a.name for a in no.names}
        elif isinstance(no, ast.ImportFrom) and no.module:
            importados.add(no.module)
    proibidos = ("repository", "memoria", "gateway", "sqlalchemy", "fastapi", "tokenizador")
    assert not [m for m in importados if any(p in m for p in proibidos)]


# --- Cartão de crédito e de débito -----------------------------------
@pytest.mark.parametrize(
    "estrategia_cls, tipo", [(PagamentoCartaoCredito, CREDITO), (PagamentoCartaoDebito, DEBITO)]
)
@pytest.mark.parametrize("resposta", [StatusPagamento.APROVADO, StatusPagamento.RECUSADO])
def test_cartao_cobra_o_token_no_gateway_e_devolve_o_resultado(estrategia_cls, tipo, resposta):
    gateway = GatewayFalso(resposta)
    pagamento = Pagamento(18.5, tipo, token_cartao="tok_abc")

    resultado = estrategia_cls(gateway).processar(pagamento, usuario=None)

    assert resultado == resposta
    assert gateway.chamadas == [("tok_abc", 18.5)]


def test_a_estrategia_so_devolve_o_resultado_e_nao_muda_o_status():
    pagamento = Pagamento(10.0, CREDITO, token_cartao="tok_x")
    PagamentoCartaoCredito(GatewayFalso()).processar(pagamento, usuario=None)
    assert pagamento.status == StatusPagamento.PENDENTE


def test_cartao_sem_token_e_recusado_pelo_gateway_real():
    from servicos_tecnicos.pagamentos.gateway import GatewayPagamento

    pagamento = Pagamento(10.0, CREDITO, token_cartao=None)
    resultado = PagamentoCartaoCredito(GatewayPagamento()).processar(pagamento, usuario=None)
    assert resultado == StatusPagamento.RECUSADO


@pytest.mark.parametrize(
    "estrategia, tipo_errado",
    [
        (PagamentoCartaoCredito(GatewayFalso()), DEBITO),
        (PagamentoCartaoDebito(GatewayFalso()), CREDITO),
        (PagamentoPix(), CREDITO),
    ],
)
def test_estrategia_recusa_pagamento_de_outro_tipo(estrategia, tipo_errado):
    with pytest.raises(ValueError):
        estrategia.processar(Pagamento(10.0, tipo_errado, token_cartao="tok"), usuario=None)


# --- PIX ---------------------------------------------------------------
def test_pix_gera_codigo_com_valor_e_validade():
    codigo = PagamentoPix().gerar_codigo(12.5, datetime(2026, 11, 18, 15, 30, 45))
    assert isinstance(codigo, str)
    assert "12.50" in codigo
    assert "20261118153045" in codigo


def test_pix_gera_codigos_diferentes_a_cada_vez():
    pix = PagamentoPix()
    validade = datetime(2026, 11, 18, 12, 0)
    assert pix.gerar_codigo(10.0, validade) != pix.gerar_codigo(10.0, validade)


def test_pix_processar_gera_o_codigo_e_deixa_o_pagamento_pendente():
    agora = datetime(2026, 11, 18, 12, 0, 0)
    pix = PagamentoPix(validade_minutos=15, relogio=lambda: agora)
    pagamento = Pagamento(30.0, PIX)

    resultado = pix.processar(pagamento, usuario=None)

    assert resultado == StatusPagamento.PENDENTE
    assert pagamento.status == StatusPagamento.PENDENTE
    assert "30.00" in pagamento.qr_code_pix
    assert "20261118121500" in pagamento.qr_code_pix  # agora + 15 minutos


# --- PagamentoService escolhe a estratégia ----------------------------
def test_service_tem_uma_estrategia_para_cada_tipo():
    service = novo_servico()
    assert set(service.metodos) == {CREDITO, DEBITO, PIX}
    assert isinstance(service.metodos[CREDITO], PagamentoCartaoCredito)
    assert isinstance(service.metodos[DEBITO], PagamentoCartaoDebito)
    assert isinstance(service.metodos[PIX], PagamentoPix)


def test_corrida_continua_cobrada_no_credito():
    gateway = GatewayFalso()
    service = novo_servico(gateway)

    pagamento = service.cobrar_corrida(EMAIL, 18.0, locacao_id=10)

    assert pagamento.tipo == CREDITO
    assert pagamento.token_cartao == "tok_credito"
    assert pagamento.status == StatusPagamento.APROVADO
    assert gateway.chamadas == [("tok_credito", 18.0)]


@pytest.mark.parametrize(
    "token, esperado",
    [("tok_debito", StatusPagamento.APROVADO), (TOKEN_CARTAO_RECUSADO, StatusPagamento.RECUSADO)],
)
def test_pacote_no_debito_usa_o_cartao_de_debito(token, esperado):
    from servicos_tecnicos.pagamentos.gateway import GatewayPagamento

    service = novo_servico(GatewayPagamento(), debito=token)

    pagamento = service.cobrar_pacote(EMAIL, 27.0, pacote_id=7, tipo=DEBITO)

    assert pagamento.tipo == DEBITO
    assert pagamento.token_cartao == token
    assert pagamento.status == esperado
    assert pagamento.pacote_id == 7


def test_debito_sem_cartao_de_debito_devolve_400_e_nao_grava_pagamento():
    service = novo_servico(debito=None)

    with pytest.raises(HTTPException) as erro:
        service.cobrar_pacote(EMAIL, 27.0, pacote_id=7, tipo=DEBITO)

    assert erro.value.status_code == 400
    assert service.pagamento_repo.list_all() == []


def test_pix_pelo_service_fica_pendente_com_codigo_e_sem_cartao():
    gateway = GatewayFalso()
    service = novo_servico(gateway, credito=None, debito=None)

    pagamento = service.cobrar_pacote(EMAIL, 27.0, pacote_id=7, tipo=PIX)

    assert pagamento.tipo == PIX
    assert pagamento.status == StatusPagamento.PENDENTE
    assert pagamento.token_cartao is None
    assert "27.00" in pagamento.qr_code_pix
    assert gateway.chamadas == []  # PIX não passa pelo gateway de cartão


def test_service_chama_processar_da_estrategia_do_tipo_sem_if():
    class Espiao(MetodoPagamento):
        tipo = DEBITO

        def __init__(self):
            self.chamadas = []

        def processar(self, pagamento, usuario):
            self.chamadas.append((pagamento, usuario))
            return StatusPagamento.RECUSADO

    espiao = Espiao()
    dono = SimpleNamespace(email=EMAIL)
    service = novo_servico(usuario_repo=SimpleNamespace(get_by_email=lambda email: dono))
    service.metodos[DEBITO] = espiao

    pagamento = service.cobrar_pacote(EMAIL, 27.0, pacote_id=7, tipo=DEBITO)

    assert espiao.chamadas == [(pagamento, dono)]  # recebeu o pagamento e o usuário
    assert pagamento.status == StatusPagamento.RECUSADO


def test_tipo_sem_estrategia_devolve_400():
    service = novo_servico()
    del service.metodos[PIX]

    with pytest.raises(HTTPException) as erro:
        service.cobrar_pacote(EMAIL, 27.0, pacote_id=7, tipo=PIX)

    assert erro.value.status_code == 400
    assert service.pagamento_repo.list_all() == []


# --- Classes abstratas de verdade ([A25]) ------------------------------
from dominio.pagamento.metodos_pagamento import _PagamentoCartao  # noqa: E402


def test_metodo_pagamento_continua_abstrata_por_processar():
    assert "processar" in MetodoPagamento.__abstractmethods__


def test_pagamento_cartao_nao_pode_ser_instanciado():
    with pytest.raises(TypeError):
        _PagamentoCartao(GatewayFalso())


def test_tipo_e_o_metodo_abstrato_do_pagamento_cartao():
    assert _PagamentoCartao.__abstractmethods__ == frozenset({"tipo"})


@pytest.mark.parametrize(
    "classe, tipo", [(PagamentoCartaoCredito, CREDITO), (PagamentoCartaoDebito, DEBITO)]
)
def test_credito_e_debito_continuam_instanciaveis_com_o_mesmo_tipo(classe, tipo):
    estrategia = classe(GatewayFalso())
    assert isinstance(estrategia, _PagamentoCartao)
    assert estrategia.tipo == tipo
    assert classe.tipo == tipo  # continua atributo de classe, como no documento


def test_cartao_sem_tipo_tambem_e_abstrato():
    class SemTipo(_PagamentoCartao):
        pass

    with pytest.raises(TypeError):
        SemTipo(GatewayFalso())
