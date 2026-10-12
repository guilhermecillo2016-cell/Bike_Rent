import pytest
from fastapi.testclient import TestClient

from main import app
from dominio.usuario import service as usuario_service
from dominio.estacao.schemas import EstacaoCreate
from dominio.estacao import service as estacao_service
from dominio.bicicleta.schemas import BicicletaCreate
from dominio.bicicleta import service as bicicleta_service
from servicos_tecnicos.banco_de_dados import memoria
from servicos_tecnicos.banco_de_dados.enums import StatusBicicleta
from servicos_tecnicos.banco_de_dados.models import UsuarioORM
from servicos_tecnicos.banco_de_dados.enums import PapelUsuario


@pytest.fixture(autouse=True)
def _limpa():
    memoria.estacoes.clear()
    memoria.bicicletas.clear()
    app.dependency_overrides[usuario_service.get_current_user] = lambda: UsuarioORM(
        nome="Ciclista", email="c@x.com", senha_hash="x", papel=PapelUsuario.CICLISTA
    )
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


def _estacao_com_bikes(qtd=2):
    est = estacao_service.criar_estacao(
        EstacaoCreate(nome="E1", endereco="Rua A", latitude=0, longitude=0, capacidade_total=10)
    )
    bikes = [bicicleta_service.cadastrar_bicicleta(BicicletaCreate(estacao_id=est.id)) for _ in range(qtd)]
    return est, bikes


def test_ok(client):
    _, (bike, _) = _estacao_com_bikes()
    r = client.post("/webclient/qr/validar", json={"qr_code": bike.qr_code})
    assert r.status_code == 200
    assert r.json()["id"] == bike.id


def test_qr_inexistente(client):
    r = client.post("/webclient/qr/validar", json={"qr_code": "BIKE-NAOEXISTE"})
    assert r.status_code == 404
    assert "escanear" in r.json()["detail"]


@pytest.mark.parametrize("st", [
    StatusBicicleta.EM_MANUTENCAO, StatusBicicleta.BLOQUEADA, StatusBicicleta.EM_USO,
])
def test_inapta_sugere_outras_da_mesma_estacao(client, st):
    _, (ruim, boa) = _estacao_com_bikes()
    bicicleta_service.set_status(ruim.id, st)
    r = client.post("/webclient/qr/validar", json={"qr_code": ruim.qr_code})
    assert r.status_code == 409
    corpo = r.json()
    assert "indisponível" in corpo["detail"]
    assert [s["id"] for s in corpo["sugestoes"]] == [boa.id]


def test_sem_token_da_401():
    app.dependency_overrides.clear()
    r = TestClient(app).post("/webclient/qr/validar", json={"qr_code": "x"})
    assert r.status_code == 401