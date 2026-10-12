from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, status

from dominio.pacote.service import CATALOGO_PACOTES, PacoteService
from servicos_tecnicos.banco_de_dados.enums import StatusPagamento
from servicos_tecnicos.banco_de_dados.models import PacoteMinutosORM

AGORA = datetime(2026, 10, 12, 12, 0)
EMAIL = "ana@exemplo.com"


# --- Fakes ------------------------------------------------------------
class FakePacoteRepo:
    def __init__(self):
        self.itens = {}

    def create(self, email_usuario, minutos_totais, data_validade):
        pacote = PacoteMinutosORM(
            id=len(self.itens) + 1,
            usuario_email=email_usuario,
            minutos_totais=minutos_totais,
            minutos_restantes=0,
            data_validade=data_validade,
            ativo=False,
        )
        self.itens[pacote.id] = pacote
        return pacote

    def get_by_id(self, pacote_id):
        return self.itens.get(pacote_id)

    def list_by_email(self, email_usuario):
        return [p for p in self.itens.values() if p.usuario_email == email_usuario]


class FakePagamentoService:
    def __init__(self, resultado=StatusPagamento.APROVADO, tem_cartao=True):
        self.resultado = resultado
        self.tem_cartao = tem_cartao
        self.cobrancas = []

    def exigir_cartao_credito(self, email):
        if not self.tem_cartao:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="sem cartão")

    def cobrar_pacote(self, email, valor, pacote_id):
        self.cobrancas.append((email, valor, pacote_id))
        return SimpleNamespace(status=self.resultado)


@pytest.fixture
def repo():
    return FakePacoteRepo()


@pytest.fixture
def pagamentos():
    return FakePagamentoService()


@pytest.fixture
def service(repo, pagamentos):
    return PacoteService(pagamentos, pacote_repo=repo, relogio=lambda: AGORA)


def novo_pacote(repo, restantes, dias, email=EMAIL, ativo=True):
    p = repo.create(email, restantes, AGORA + timedelta(days=dias))
    p.minutos_restantes = restantes
    p.ativo = ativo
    return p


def codigo(exc_info):
    return exc_info.value.status_code


# --- Catálogo ---------------------------------------------------------
def test_catalogo_tem_30_60_e_120_minutos(service):
    assert [i.minutos for i in service.listar_catalogo()] == [30, 60, 120]


# --- Compra -----------------------------------------------------------
def test_compra_aprovada_ativa_e_credita_saldo(service, repo, pagamentos):
    item = CATALOGO_PACOTES[1]  # 60 min

    pacote, pagamento = service.comprar_pacote(EMAIL, item.id)

    assert pagamento.status == StatusPagamento.APROVADO
    assert pacote.ativo is True
    assert pacote.minutos_totais == 60
    assert pacote.minutos_restantes == 60
    assert pacote.data_validade == AGORA + timedelta(days=item.validade_dias)
    assert pagamentos.cobrancas == [(EMAIL, item.preco, pacote.id)]
    assert repo.get_by_id(pacote.id) is pacote


def test_compra_recusada_deixa_pacote_inativo_e_sem_saldo(repo):
    service = PacoteService(
        FakePagamentoService(resultado=StatusPagamento.RECUSADO),
        pacote_repo=repo,
        relogio=lambda: AGORA,
    )

    pacote, pagamento = service.comprar_pacote(EMAIL, 1)

    assert pagamento.status == StatusPagamento.RECUSADO
    assert pacote.ativo is False
    assert pacote.minutos_restantes == 0
    assert service.saldo_minutos(EMAIL) == 0


def test_compra_item_inexistente_levanta_404(service, repo):
    with pytest.raises(HTTPException) as exc:
        service.comprar_pacote(EMAIL, 999)
    assert codigo(exc) == status.HTTP_404_NOT_FOUND
    assert repo.itens == {}


def test_compra_sem_cartao_levanta_400_e_nao_cria_pacote(repo):
    service = PacoteService(
        FakePagamentoService(tem_cartao=False), pacote_repo=repo, relogio=lambda: AGORA
    )
    with pytest.raises(HTTPException) as exc:
        service.comprar_pacote(EMAIL, 1)
    assert codigo(exc) == status.HTTP_400_BAD_REQUEST
    assert repo.itens == {}


# --- saldo_minutos ----------------------------------------------------
def test_saldo_soma_pacotes_ativos_e_validos(service, repo):
    novo_pacote(repo, 30, dias=5)
    novo_pacote(repo, 20, dias=10)
    assert service.saldo_minutos(EMAIL) == 50


def test_saldo_ignora_inativo_vencido_zerado_e_de_outro_usuario(service, repo):
    novo_pacote(repo, 30, dias=5)                       # conta
    novo_pacote(repo, 99, dias=5, ativo=False)          # inativo
    vencido = novo_pacote(repo, 99, dias=-1)            # vencido
    zerado = novo_pacote(repo, 0, dias=5)               # zerado
    novo_pacote(repo, 99, dias=5, email="b@exemplo.com")  # outro usuário

    assert service.saldo_minutos(EMAIL) == 30
    assert vencido.ativo is False and zerado.ativo is False


def test_pacote_que_vence_agora_nao_conta(service, repo):
    p = novo_pacote(repo, 30, dias=0)  # data_validade == AGORA
    assert service.saldo_minutos(EMAIL) == 0
    assert p.ativo is False


# --- abater_minutos ---------------------------------------------------
def test_abate_primeiro_o_que_vence_antes(service, repo):
    longo = novo_pacote(repo, 30, dias=20)
    curto = novo_pacote(repo, 30, dias=2)

    abatidos = service.abater_minutos(EMAIL, 10)

    assert abatidos == 10
    assert curto.minutos_restantes == 20
    assert longo.minutos_restantes == 30


def test_abate_atravessa_pacotes_e_desativa_o_zerado(service, repo):
    curto = novo_pacote(repo, 10, dias=2)
    longo = novo_pacote(repo, 30, dias=20)

    abatidos = service.abater_minutos(EMAIL, 25)

    assert abatidos == 25
    assert curto.minutos_restantes == 0 and curto.ativo is False
    assert longo.minutos_restantes == 15 and longo.ativo is True


def test_abate_parcial_devolve_o_que_conseguiu(service, repo):
    novo_pacote(repo, 10, dias=2)
    novo_pacote(repo, 5, dias=3)

    assert service.abater_minutos(EMAIL, 40) == 15
    assert service.saldo_minutos(EMAIL) == 0


def test_abate_sem_pacotes_devolve_zero(service):
    assert service.abater_minutos(EMAIL, 10) == 0


def test_abate_zero_nao_mexe_em_nada(service, repo):
    p = novo_pacote(repo, 10, dias=2)
    assert service.abater_minutos(EMAIL, 0) == 0
    assert p.minutos_restantes == 10


def test_abate_negativo_levanta_400(service):
    with pytest.raises(HTTPException) as exc:
        service.abater_minutos(EMAIL, -1)
    assert codigo(exc) == status.HTTP_400_BAD_REQUEST


def test_abate_ignora_pacote_vencido(service, repo):
    vencido = novo_pacote(repo, 30, dias=-1)
    assert service.abater_minutos(EMAIL, 10) == 0
    assert vencido.minutos_restantes == 30  # intacto


# --- listar_pacotes ---------------------------------------------------
def test_listar_atualiza_situacao_e_so_traz_do_usuario(service, repo):
    novo_pacote(repo, 30, dias=5)
    vencido = novo_pacote(repo, 30, dias=-1)
    novo_pacote(repo, 30, dias=5, email="b@exemplo.com")

    lista = service.listar_pacotes(EMAIL)

    assert len(lista) == 2
    assert vencido.ativo is False