from fastapi import FastAPI
from fastapi.testclient import TestClient

from apresentacao.webclient import router
from dominio.estacao import disponibilidade
from tests.test_estacao_disponibilidade import BLOQUEADA, IBIRAPUERA, ORIGEM, PAULISTA, SE


def montar_client(monkeypatch):
    estacoes = [IBIRAPUERA, SE, PAULISTA, BLOQUEADA]
    monkeypatch.setattr(disponibilidade, "_estacoes", lambda: estacoes)
    monkeypatch.setattr(disponibilidade, "_bicicletas_disponiveis", lambda e: 4)
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_get_estacoes_devolve_disponibilidade(monkeypatch):
    r = montar_client(monkeypatch).get("/webclient/estacoes")
    assert r.status_code == 200
    primeiro = r.json()[0]
    assert set(primeiro) == {
        "id", "nome", "endereco", "status",
        "bicicletas_disponiveis", "vagas_livres", "latitude", "longitude",
        "distancia_metros",
    }
    assert primeiro["distancia_metros"] is None


def test_get_estacoes_com_lat_lng_ordena_por_distancia(monkeypatch):
    lat, lng = ORIGEM
    r = montar_client(monkeypatch).get(f"/webclient/estacoes?lat={lat}&lng={lng}")
    assert r.status_code == 200
    distancias = [e["distancia_metros"] for e in r.json()]
    assert distancias == sorted(distancias)


def test_get_estacoes_so_com_lat_devolve_400(monkeypatch):
    r = montar_client(monkeypatch).get("/webclient/estacoes?lat=-23.5")
    assert r.status_code == 400


def test_get_estacoes_lat_invalida_devolve_422(monkeypatch):
    r = montar_client(monkeypatch).get("/webclient/estacoes?lat=95&lng=0")
    assert r.status_code == 422


def test_proximas_com_vaga_exclui_bloqueada_e_cheia(monkeypatch):
    lat, lng = ORIGEM
    r = montar_client(monkeypatch).get(
        f"/webclient/estacoes/proximas-com-vaga?lat={lat}&lng={lng}&n=10"
    )
    assert r.status_code == 200
    assert [e["id"] for e in r.json()] == [1, 2]


def test_proximas_com_vaga_exige_lat_e_lng(monkeypatch):
    r = montar_client(monkeypatch).get("/webclient/estacoes/proximas-com-vaga?lat=-23.5")
    assert r.status_code == 422