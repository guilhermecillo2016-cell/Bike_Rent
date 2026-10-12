import pytest
from servicos_tecnicos.iot import definir_trava, obter_trava, ErroTrava
from servicos_tecnicos.iot.mock import ModoTrava, TravaInteligenteMock


@pytest.fixture(autouse=True)
def _reset():
    yield
    definir_trava(None)


def test_sucesso():
    trava = TravaInteligenteMock(ModoTrava.SUCESSO)
    assert trava.abrir(1) is True
    assert trava.confirmar_travamento(1, 2) is True
    assert trava.travas == [(1, 2)]


def test_forcar_timeout():
    definir_trava(TravaInteligenteMock(ModoTrava.TIMEOUT))
    assert obter_trava().abrir(1) is False


def test_falha():
    with pytest.raises(ErroTrava):
        TravaInteligenteMock(ModoTrava.FALHA).abrir(1)