from types import SimpleNamespace

import pytest
from fastapi import HTTPException, status

from dominio.estacao import disponibilidade
from servicos_tecnicos.banco_de_dados.enums import StatusEstacao

ORIGEM = (-23.5629, -46.6544)  # perto da Paulista


def est(id, nome, lat, lng, vagas, st=StatusEstacao.OPERACIONAL):
    return SimpleNamespace(
        id=id, nome=nome, endereco=f"Rua {nome}", status=st,
        vagas_disponiveis=vagas, latitude=lat, longitude=lng,
    )


PAULISTA = est(1, "Paulista", -23.5614, -46.6559, vagas=5)
SE = est(2, "Sé", -23.5505, -46.6333, vagas=3)
IBIRAPUERA = est(3, "Ibirapuera", -23.5874, -46.6576, vagas=0)  # cheia
BLOQUEADA = est(4, "Bloqueada", -23.5620, -46.6550, vagas=9, st=StatusEstacao.BLOQUEADA)

BICICLETAS = {1: 4, 2: 0, 3: 7, 4: 6}


def contar(estacao):
    return BICICLETAS[estacao.id]


def codigo(exc_info):
    return exc_info.value.status_code


# --- listar_estacoes --------------------------------------------------
def test_lista_com_disponibilidade_endereco_e_status():
    itens = disponibilidade.listar_estacoes(
        estacoes=[PAULISTA, SE], contar_bicicletas=contar
    )

    assert [i.id for i in itens] == [1, 2]  # sem lat/lng: ordem do cadastro
    paulista = itens[0]
    assert paulista.nome == "Paulista"
    assert paulista.endereco == "Rua Paulista"
    assert paulista.status == StatusEstacao.OPERACIONAL
    assert paulista.bicicletas_disponiveis == 4
    assert paulista.vagas_livres == 5
    assert paulista.distancia_metros is None


def test_com_lat_lng_ordena_por_distancia_e_informa_a_distancia():
    itens = disponibilidade.listar_estacoes(
        *ORIGEM, estacoes=[IBIRAPUERA, SE, PAULISTA], contar_bicicletas=contar
    )

    assert [i.id for i in itens] == [1, 2, 3]
    assert 150 < itens[0].distancia_metros < 300
    assert itens[0].distancia_metros < itens[1].distancia_metros < itens[2].distancia_metros


def test_estacao_bloqueada_aparece_com_status_mas_sem_opcao():
    (item,) = disponibilidade.listar_estacoes(
        estacoes=[BLOQUEADA], contar_bicicletas=contar
    )

    assert item.status == StatusEstacao.BLOQUEADA
    assert item.bicicletas_disponiveis == 0
    assert item.vagas_livres == 0


def test_so_lat_ou_so_lng_levanta_400():
    for args in [(-23.5, None), (None, -46.6)]:
        with pytest.raises(HTTPException) as exc:
            disponibilidade.listar_estacoes(*args, estacoes=[PAULISTA])
        assert codigo(exc) == status.HTTP_400_BAD_REQUEST


def test_coordenada_fora_do_intervalo_levanta_400():
    with pytest.raises(HTTPException) as exc:
        disponibilidade.listar_estacoes(95, 0, estacoes=[PAULISTA])
    assert codigo(exc) == status.HTTP_400_BAD_REQUEST


def test_sem_estacoes_devolve_lista_vazia():
    assert disponibilidade.listar_estacoes(estacoes=[]) == []


# --- proximas_com_vaga ------------------------------------------------
def test_proximas_com_vaga_exclui_bloqueada_e_estacao_cheia():
    itens = disponibilidade.proximas_com_vaga(
        *ORIGEM, 10,
        estacoes=[PAULISTA, SE, IBIRAPUERA, BLOQUEADA],
        contar_bicicletas=contar,
    )

    assert [i.id for i in itens] == [1, 2]  # 3 sem vaga, 4 bloqueada
    assert all(i.vagas_livres > 0 for i in itens)


def test_proximas_com_vaga_ordena_por_distancia_e_limita_a_n():
    itens = disponibilidade.proximas_com_vaga(
        *ORIGEM, 1, estacoes=[SE, PAULISTA], contar_bicicletas=contar
    )

    assert [i.id for i in itens] == [1]
    assert itens[0].distancia_metros is not None


def test_proximas_com_vaga_nenhuma_elegivel_devolve_vazio():
    assert disponibilidade.proximas_com_vaga(
        *ORIGEM, estacoes=[IBIRAPUERA, BLOQUEADA], contar_bicicletas=contar
    ) == []


def test_proximas_com_vaga_exige_lat_e_lng():
    with pytest.raises(HTTPException) as exc:
        disponibilidade.proximas_com_vaga(None, None, estacoes=[PAULISTA])
    assert codigo(exc) == status.HTTP_400_BAD_REQUEST