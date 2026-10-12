from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException

from dominio.locacao import service as locacao_service, tarifa
from servicos_tecnicos.banco_de_dados import memoria, repository_locacao
from servicos_tecnicos.banco_de_dados import repository_pacote
from dominio.estacao import service as estacao_service
from dominio.estacao.schemas import EstacaoCreate

EMAIL = "c@x.com"


@pytest.fixture(autouse=True)
def _limpa():
    for d in (memoria.estacoes, memoria.bicicletas, memoria.locacoes, memoria.pacotes):
        d.clear()
    yield


def _locacao_iniciada_ha(segundos):
    est = estacao_service.criar_estacao(
        EstacaoCreate(nome="E1", endereco="Rua A", latitude=0, longitude=0, capacidade_total=5)
    )
    loc = repository_locacao.create(EMAIL, bicicleta_id=1, estacao_origem_id=est.id)
    loc.data_hora_inicio = datetime.now() - timedelta(seconds=segundos)
    return loc


def _pacote(minutos, ativo=True, validade_dias=7):
    p = repository_pacote.create(EMAIL, minutos, datetime.now() + timedelta(days=validade_dias))
    p.ativo = ativo
    return p


def test_sem_corrida_ativa_404():
    with pytest.raises(HTTPException) as e:
        locacao_service.obter_locacao_ativa(EMAIL)
    assert e.value.status_code == 404
    assert "corrida" in e.value.detail


def test_duracao_calculada_no_servidor_sem_pacote():
    loc = _locacao_iniciada_ha(90)  # 1min30 -> 2 min iniciados
    a = locacao_service.calcular_andamento(loc)
    assert a.duracao_minutos == 2
    assert a.minutos_pacote == 0
    assert a.custo_estimado == tarifa.calcular_valor(2)
    assert a.estacao_origem_nome == "E1"


def test_pacote_abate_parte_da_corrida():
    loc = _locacao_iniciada_ha(8 * 60 - 30)  # 8 min iniciados
    _pacote(5)
    a = locacao_service.calcular_andamento(loc)
    assert a.minutos_pacote == 5
    assert a.custo_estimado == tarifa.calcular_valor(3)


def test_pacote_cobre_tudo_custo_zero():
    loc = _locacao_iniciada_ha(120)
    _pacote(30)
    a = locacao_service.calcular_andamento(loc)
    assert a.custo_estimado == 0.0


def test_pacote_inativo_ou_vencido_nao_conta():
    loc = _locacao_iniciada_ha(120)
    _pacote(30, ativo=False)
    _pacote(30, validade_dias=-1)
    a = locacao_service.calcular_andamento(loc)
    assert a.minutos_pacote == 0
    assert a.custo_estimado == tarifa.calcular_valor(2)


def test_chamadas_seguidas_refletem_o_relogio_do_servidor():
    loc = _locacao_iniciada_ha(30)
    depois = datetime.now() + timedelta(minutes=10)
    a = locacao_service.calcular_andamento(loc, agora=depois)
    assert a.duracao_minutos >= 11  # simula reconexão do celular (extensão *a)