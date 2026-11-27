"""
tests/test_estados_bicicleta.py
---------------------------------
finalizar_uso() (padrão State da Bicicleta): só a bicicleta EM_USO termina uma
corrida; nos demais estados é erro de domínio (409), como iniciar_uso().
"""

import pytest
from fastapi import HTTPException

from dominio.bicicleta.bicicleta import Bicicleta
from dominio.erros import ConflitoDeRegra
from servicos_tecnicos.banco_de_dados.enums import StatusBicicleta


def _bicicleta(status):
    return Bicicleta(1, "BIKE-TESTE", status=status)


# --- EM_USO: o único estado que aceita -------------------------------
def test_em_uso_sem_bloqueio_volta_a_disponivel():
    b = _bicicleta(StatusBicicleta.EM_USO)
    assert b.finalizar_uso() is False
    assert b.status == StatusBicicleta.DISPONIVEL
    assert b.bloqueio_pendente is False


def test_em_uso_com_bloqueio_pendente_vai_para_manutencao_e_limpa_o_flag():
    b = _bicicleta(StatusBicicleta.EM_USO)
    b.bloqueio_pendente = True
    assert b.finalizar_uso() is True
    assert b.status == StatusBicicleta.EM_MANUTENCAO
    assert b.bloqueio_pendente is False


# --- os outros três estados recusam ----------------------------------
@pytest.mark.parametrize(
    "status",
    [StatusBicicleta.DISPONIVEL, StatusBicicleta.EM_MANUTENCAO, StatusBicicleta.BLOQUEADA],
)
def test_outros_estados_levantam_conflito_409_e_nao_mudam_nada(status):
    b = _bicicleta(status)
    with pytest.raises(ConflitoDeRegra) as erro:
        b.finalizar_uso()
    assert erro.value.status_code == 409
    assert b.status == status
    assert b.bloqueio_pendente is False


@pytest.mark.parametrize(
    "status",
    [StatusBicicleta.DISPONIVEL, StatusBicicleta.EM_MANUTENCAO, StatusBicicleta.BLOQUEADA],
)
def test_bloqueio_pendente_nao_e_limpo_quando_o_evento_e_recusado(status):
    b = _bicicleta(status)
    b.bloqueio_pendente = True
    with pytest.raises(ConflitoDeRegra):
        b.finalizar_uso()
    assert b.status == status
    assert b.bloqueio_pendente is True


def test_o_erro_e_um_http_exception_para_a_api():
    # ErroDeDominio herda de HTTPException: o FastAPI responde 409 sozinho.
    with pytest.raises(HTTPException) as erro:
        _bicicleta(StatusBicicleta.DISPONIVEL).finalizar_uso()
    assert erro.value.status_code == 409


# --- simetria com iniciar_uso() --------------------------------------
@pytest.mark.parametrize(
    "status",
    [StatusBicicleta.EM_USO, StatusBicicleta.EM_MANUTENCAO, StatusBicicleta.BLOQUEADA],
)
def test_iniciar_uso_so_aceita_disponivel(status):
    with pytest.raises(ConflitoDeRegra):
        _bicicleta(status).iniciar_uso()


def test_ciclo_completo_disponivel_em_uso_disponivel():
    b = _bicicleta(StatusBicicleta.DISPONIVEL)
    b.iniciar_uso()
    assert b.status == StatusBicicleta.EM_USO
    b.finalizar_uso()
    assert b.status == StatusBicicleta.DISPONIVEL


# --- EstadoBicicleta é abstrata de verdade ([A25]) -------------------
from dominio.bicicleta.estados_bicicleta import (  # noqa: E402
    Bloqueada,
    Disponivel,
    EmManutencao,
    EmUso,
    EstadoBicicleta,
    estado_de,
)


def test_estado_bicicleta_nao_pode_ser_instanciada():
    with pytest.raises(TypeError):
        EstadoBicicleta()


def test_status_e_o_metodo_abstrato_da_classe_base():
    assert EstadoBicicleta.__abstractmethods__ == frozenset({"status"})


@pytest.mark.parametrize(
    "classe, status",
    [
        (Disponivel, StatusBicicleta.DISPONIVEL),
        (EmUso, StatusBicicleta.EM_USO),
        (EmManutencao, StatusBicicleta.EM_MANUTENCAO),
        (Bloqueada, StatusBicicleta.BLOQUEADA),
    ],
)
def test_estados_concretos_continuam_instanciaveis_com_o_mesmo_status(classe, status):
    estado = classe()
    assert isinstance(estado, EstadoBicicleta)
    assert estado.status == status
    assert classe.status == status  # continua atributo de classe, como no documento
    assert isinstance(estado_de(status), classe)


def test_subclasse_sem_status_tambem_e_abstrata():
    class SemStatus(EstadoBicicleta):
        pass

    with pytest.raises(TypeError):
        SemStatus()
