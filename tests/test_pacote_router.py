from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from apresentacao.webclient import router
from dominio.pacote import service as pacote_service
from dominio.pacote.service import PacoteService
from dominio.usuario import service as usuario_service
from servicos_tecnicos.banco_de_dados.enums import StatusPagamento
from tests.test_pacote_service import AGORA, EMAIL, FakePacoteRepo, FakePagamentoService


def montar_client(monkeypatch, resultado=StatusPagamento.APROVADO):
    service = PacoteService(
        FakePagamentoService(resultado=resultado),
        pacote_repo=FakePacoteRepo(),
        relogio=lambda: AGORA,
    )
    monkeypatch.setattr(pacote_service, "_servico", lambda: service)
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[usuario_service.get_current_user] = lambda: SimpleNamespace(
        email=EMAIL
    )
    return TestClient(app)


def test_get_catalogo(monkeypatch):
    r = montar_client(monkeypatch).get("/webclient/pacotes/catalogo")
    assert r.status_code == 200
    assert [i["minutos"] for i in r.json()] == [30, 60, 120]


def test_post_compra_aprovada(monkeypatch):
    r = montar_client(monkeypatch).post("/webclient/pacotes", json={"item_id": 2})
    assert r.status_code == 201
    corpo = r.json()
    assert corpo["pagamento_status"] == "APROVADO"
    assert corpo["pacote"]["ativo"] is True
    assert corpo["pacote"]["minutos_restantes"] == 60


def test_post_compra_recusada_devolve_pacote_inativo(monkeypatch):
    client = montar_client(monkeypatch, StatusPagamento.RECUSADO)
    r = client.post("/webclient/pacotes", json={"item_id": 1})
    assert r.status_code == 201
    corpo = r.json()
    assert corpo["pagamento_status"] == "RECUSADO"
    assert corpo["pacote"]["ativo"] is False
    assert corpo["pacote"]["minutos_restantes"] == 0


def test_post_item_invalido_404(monkeypatch):
    r = montar_client(monkeypatch).post("/webclient/pacotes", json={"item_id": 999})
    assert r.status_code == 404


def test_get_lista_pacotes_do_ciclista(monkeypatch):
    client = montar_client(monkeypatch)
    client.post("/webclient/pacotes", json={"item_id": 1})
    r = client.get("/webclient/pacotes")
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["minutos_restantes"] == 30