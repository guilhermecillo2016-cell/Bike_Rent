import pytest
from fastapi.testclient import TestClient

from servicos_tecnicos.iot import get_trava, set_trava
from servicos_tecnicos.iot.trava_inteligente import TravaInteligente
from servicos_tecnicos.iot.mock import TravaMock, ModoTrava


# ---------- Mock em si ----------
def test_abrir_sucesso():
    assert TravaMock(ModoTrava.SUCESSO).abrir(1) is True

def test_abrir_timeout_forcado():
    # critério de aceite 1: forçar timeout nos testes
    assert TravaMock(ModoTrava.TIMEOUT, timeout_s=0).abrir(1) is False

def test_abrir_falha():
    assert TravaMock(ModoTrava.FALHA).abrir(1) is False

def test_confirmar_travamento_por_modo():
    assert TravaMock(ModoTrava.SUCESSO).confirmar_travamento(1, 1) is True
    assert TravaMock(ModoTrava.FALHA).confirmar_travamento(1, 1) is False


# ---------- Variável de ambiente ----------
def test_modo_via_env(monkeypatch):
    monkeypatch.setenv("IOT_MODO", "falha")
    assert TravaMock().modo == ModoTrava.FALHA

def test_modo_env_invalido(monkeypatch):
    monkeypatch.setenv("IOT_MODO", "xyz")
    with pytest.raises(ValueError):
        TravaMock()


# ---------- Fábrica ----------
def test_mock_implementa_a_interface():
    assert isinstance(get_trava(), TravaInteligente)

def test_set_trava_troca_implementacao():
    original = get_trava()
    try:
        set_trava(TravaMock(ModoTrava.FALHA))
        assert get_trava().abrir(1) is False
    finally:
        set_trava(original)


# ---------- Rota ----------
def test_rota_travamento():
    from main import app
    client = TestClient(app)
    original = get_trava()
    try:
        set_trava(TravaMock(ModoTrava.SUCESSO))
        r = client.post("/iot/travamento", json={"bicicleta_id": 1, "estacao_id": 1})
        assert r.status_code == 200
        assert r.json() == {"confirmado": True}

        set_trava(TravaMock(ModoTrava.FALHA))
        r = client.post("/iot/travamento", json={"bicicleta_id": 1, "estacao_id": 1})
        assert r.json() == {"confirmado": False}
    finally:
        set_trava(original)

def test_rota_payload_invalido():
    from main import app
    r = TestClient(app).post("/iot/travamento", json={"bicicleta_id": 1})
    assert r.status_code == 422
def test_rota_id_nao_inteiro():
    from main import app
    r = TestClient(app).post("/iot/travamento", json={"bicicleta_id": "abc", "estacao_id": 1})
    assert r.status_code == 422