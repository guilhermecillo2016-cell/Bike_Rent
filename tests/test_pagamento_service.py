from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, status

from dominio.pagamento.service import PagamentoService  # ajuste ao caminho real do service
from servicos_tecnicos.banco_de_dados.enums import StatusPagamento, TipoPagamento
from servicos_tecnicos.banco_de_dados.models import PagamentoORM
from servicos_tecnicos.pagamentos.gateway import TOKEN_CARTAO_RECUSADO

EMAIL = "ana@exemplo.com"


# --- Fakes em memória -------------------------------------------------
class FakePagamentoRepo:
    def __init__(self):
        self.itens = {}

    def create(self, valor, tipo, locacao_id=None, pacote_id=None, token_cartao=None):
        pagamento = PagamentoORM(
            id=len(self.itens) + 1,
            valor=valor,
            tipo=tipo,
            data_hora=datetime.now(),
            locacao_id=locacao_id,
            pacote_id=pacote_id,
            token_cartao=token_cartao,
        )
        self.itens[pagamento.id] = pagamento
        return pagamento

    def get_by_id(self, pagamento_id):
        return self.itens.get(pagamento_id)

    def list_all(self):
        return list(self.itens.values())


class FakeCartaoRepo:
    def __init__(self, cartoes=None):
        self.cartoes = cartoes or {}

    def get_credito_by_email(self, email):
        return self.cartoes.get(email)


class FakeLocacaoRepo:
    def __init__(self, ids):
        self.ids = set(ids)

    def get_by_id(self, locacao_id):
        return object() if locacao_id in self.ids else None


class GatewaySpy:
    def __init__(self):
        self.chamadas = []

    def cobrar(self, token, valor):
        self.chamadas.append((token, valor))
        return StatusPagamento.APROVADO


def cartao(token="tok_ok"):
    return SimpleNamespace(token=token, tipo=TipoPagamento.CARTAO_CREDITO)


@pytest.fixture
def pagamentos():
    return FakePagamentoRepo()


@pytest.fixture
def service(pagamentos):
    return PagamentoService(
        pagamento_repo=pagamentos,
        cartao_repo=FakeCartaoRepo({EMAIL: cartao()}),
        locacao_repo=FakeLocacaoRepo({10}),
    )


def codigo(exc_info):
    return exc_info.value.status_code


# --- cobrar_corrida ---------------------------------------------------
def test_cobrar_corrida_aprovada(service, pagamentos):
    p = service.cobrar_corrida(EMAIL, 18.0, locacao_id=10)

    assert p.status == StatusPagamento.APROVADO
    assert p.tipo == TipoPagamento.CARTAO_CREDITO
    assert p.valor == 18.0
    assert p.locacao_id == 10
    assert p.pacote_id is None
    assert p.token_cartao == "tok_ok"
    assert pagamentos.get_by_id(p.id) is p  # foi gravado


def test_cobrar_corrida_recusada_nao_lanca_excecao(pagamentos):
    service = PagamentoService(
        pagamento_repo=pagamentos,
        cartao_repo=FakeCartaoRepo({EMAIL: cartao(TOKEN_CARTAO_RECUSADO)}),
    )

    p = service.cobrar_corrida(EMAIL, 18.0, locacao_id=10)

    assert p.status == StatusPagamento.RECUSADO
    assert pagamentos.get_by_id(p.id) is p  # recusa também é gravada


def test_cobrar_corrida_locacao_inexistente(service, pagamentos):
    with pytest.raises(HTTPException) as exc:
        service.cobrar_corrida(EMAIL, 18.0, locacao_id=999)
    assert codigo(exc) == status.HTTP_404_NOT_FOUND
    assert pagamentos.list_all() == []


# --- cobrar_pacote ----------------------------------------------------
def test_cobrar_pacote_aprovado(service):
    p = service.cobrar_pacote(EMAIL, 50.0, pacote_id=7)

    assert p.status == StatusPagamento.APROVADO
    assert p.pacote_id == 7
    assert p.locacao_id is None


def test_cobrar_pacote_recusado(pagamentos):
    service = PagamentoService(
        pagamento_repo=pagamentos,
        cartao_repo=FakeCartaoRepo({EMAIL: cartao(TOKEN_CARTAO_RECUSADO)}),
    )

    p = service.cobrar_pacote(EMAIL, 50.0, pacote_id=7)

    assert p.status == StatusPagamento.RECUSADO


# --- RN-06: cartão de crédito obrigatório -----------------------------
def test_sem_cartao_de_credito_levanta_400(pagamentos):
    service = PagamentoService(
        pagamento_repo=pagamentos, cartao_repo=FakeCartaoRepo({})
    )

    with pytest.raises(HTTPException) as exc:
        service.cobrar_corrida(EMAIL, 18.0, locacao_id=10)

    assert codigo(exc) == status.HTTP_400_BAD_REQUEST
    assert pagamentos.list_all() == []


def test_exigir_cartao_credito_devolve_o_cartao(service):
    assert service.exigir_cartao_credito(EMAIL).token == "tok_ok"


def test_exigir_cartao_credito_sem_cartao_levanta_400(service):
    with pytest.raises(HTTPException) as exc:
        service.exigir_cartao_credito("outro@exemplo.com")
    assert codigo(exc) == status.HTTP_400_BAD_REQUEST


# --- Valor ------------------------------------------------------------
@pytest.mark.parametrize("valor", [0, -5, "abc", None, float("nan")])
def test_valor_invalido_levanta_400(service, pagamentos, valor):
    with pytest.raises(HTTPException) as exc:
        service.cobrar_corrida(EMAIL, valor, locacao_id=10)
    assert codigo(exc) == status.HTTP_400_BAD_REQUEST
    assert pagamentos.list_all() == []


# --- XOR locacao_id / pacote_id ---------------------------------------
@pytest.mark.parametrize("locacao_id, pacote_id", [(1, 2), (None, None)])
def test_xor_violado_levanta_400(locacao_id, pacote_id):
    with pytest.raises(HTTPException) as exc:
        PagamentoService._validar_destino(locacao_id, pacote_id)
    assert codigo(exc) == status.HTTP_400_BAD_REQUEST


@pytest.mark.parametrize("locacao_id, pacote_id", [(1, None), (None, 2)])
def test_xor_valido_nao_levanta(locacao_id, pacote_id):
    PagamentoService._validar_destino(locacao_id, pacote_id)


# --- Gateway injetado -------------------------------------------------
def test_usa_o_gateway_injetado(pagamentos):
    spy = GatewaySpy()
    service = PagamentoService(
        pagamento_repo=pagamentos,
        cartao_repo=FakeCartaoRepo({EMAIL: cartao("tok_xyz")}),
        gateway=spy,
    )

    service.cobrar_corrida(EMAIL, 18.0, locacao_id=10)

    assert spy.chamadas == [("tok_xyz", 18.0)]


# --- Consultas --------------------------------------------------------
def test_obter_pagamento_existente(service):
    criado = service.cobrar_corrida(EMAIL, 18.0, locacao_id=10)
    assert service.obter_pagamento(criado.id) is criado


def test_obter_pagamento_inexistente_levanta_404(service):
    with pytest.raises(HTTPException) as exc:
        service.obter_pagamento(999)
    assert codigo(exc) == status.HTTP_404_NOT_FOUND


def test_listar_pagamentos(service):
    service.cobrar_corrida(EMAIL, 18.0, locacao_id=10)
    service.cobrar_pacote(EMAIL, 50.0, pacote_id=7)
    assert len(service.listar_pagamentos()) == 2