import pytest
from fastapi import HTTPException

from dominio.bicicleta import service as bicicleta_service
from dominio.bicicleta.schemas import BicicletaCreate
from dominio.estacao import service as estacao_service
from dominio.estacao.schemas import EstacaoCreate
from dominio.locacao import service as locacao_service
from dominio.pagamento import service as pagamento_service
from dominio.pagamento.schemas import CartaoCreate
from servicos_tecnicos.banco_de_dados import memoria, repository_bicicleta
from servicos_tecnicos.banco_de_dados.enums import StatusBicicleta
from servicos_tecnicos.iot import definir_trava
from servicos_tecnicos.iot.mock import ModoTrava, TravaInteligenteMock

EMAIL = "c@x.com"


@pytest.fixture(autouse=True)
def _limpa():
    for d in (memoria.estacoes, memoria.bicicletas, memoria.locacoes, memoria.cartoes):
        d.clear()
    definir_trava(TravaInteligenteMock(ModoTrava.SUCESSO))
    yield
    definir_trava(None)


def _cenario(com_cartao=True, qtd=1):
    est = estacao_service.criar_estacao(
        EstacaoCreate(nome="E1", endereco="Rua A", latitude=0, longitude=0, capacidade_total=10)
    )
    bikes = [bicicleta_service.cadastrar_bicicleta(BicicletaCreate(estacao_id=est.id)) for _ in range(qtd)]
    if com_cartao:
        pagamento_service.vincular_cartao(
            EMAIL,
            CartaoCreate(numero_cartao="4111111111111111", nome_titular="Fulano",
                         validade="12/99", cvv="123"),
        )
    return est, bikes


def test_sem_cartao():
    _, (bike,) = _cenario(com_cartao=False)
    with pytest.raises(HTTPException) as e:
        locacao_service.iniciar_locacao(EMAIL, bike.qr_code)
    assert e.value.status_code == 400
    assert "cartão" in e.value.detail
    assert bike.status == StatusBicicleta.DISPONIVEL


def test_sucesso():
    est, (bike,) = _cenario()
    loc = locacao_service.iniciar_locacao(EMAIL, bike.qr_code)
    assert loc.em_andamento and loc.data_hora_inicio is not None
    assert loc.estacao_origem_id == est.id
    assert bike.status == StatusBicicleta.EM_USO
    assert bike.estacao_id is None


@pytest.mark.parametrize("modo", [ModoTrava.TIMEOUT, ModoTrava.FALHA])
def test_falha_da_trava_nao_cria_locacao(modo):
    est, (bike,) = _cenario()
    definir_trava(TravaInteligenteMock(modo))
    with pytest.raises(HTTPException) as e:
        locacao_service.iniciar_locacao(EMAIL, bike.qr_code)
    assert e.value.status_code == 503
    assert bike.status == StatusBicicleta.DISPONIVEL
    assert bike.estacao_id == est.id
    assert memoria.locacoes == {}


def test_duas_corridas_ativas():
    _, (b1, b2) = _cenario(qtd=2)
    locacao_service.iniciar_locacao(EMAIL, b1.qr_code)
    with pytest.raises(HTTPException) as e:
        locacao_service.iniciar_locacao(EMAIL, b2.qr_code)
    assert e.value.status_code == 409
    assert b2.status == StatusBicicleta.DISPONIVEL


def test_bicicleta_inapta():
    _, (bike,) = _cenario()
    bicicleta_service.set_status(bike.id, StatusBicicleta.EM_MANUTENCAO)
    with pytest.raises(bicicleta_service.BicicletaIndisponivel):
        locacao_service.iniciar_locacao(EMAIL, bike.qr_code)
    assert memoria.locacoes == {}


def test_qr_inexistente():
    _cenario()
    with pytest.raises(HTTPException) as e:
        locacao_service.iniciar_locacao(EMAIL, "BIKE-NAOEXISTE")
    assert e.value.status_code == 404