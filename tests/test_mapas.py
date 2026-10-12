from types import SimpleNamespace

from servicos_tecnicos import mapas


def est(id, lat, lng):
    return SimpleNamespace(id=id, latitude=lat, longitude=lng)


PAULISTA = est(1, -23.5614, -46.6559)
SE = est(2, -23.5505, -46.6333)
IBIRAPUERA = est(3, -23.5874, -46.6576)
ORIGEM = (-23.5629, -46.6544)  # perto da Paulista


def test_ordena_da_mais_proxima_para_a_mais_distante():
    pares = mapas.estacoes_mais_proximas(*ORIGEM, 3, estacoes=[IBIRAPUERA, SE, PAULISTA])
    assert [e.id for e, _ in pares] == [1, 2, 3]
    distancias = [d for _, d in pares]
    assert distancias == sorted(distancias)


def test_devolve_a_distancia_em_metros():
    (_, d), *_ = mapas.estacoes_mais_proximas(*ORIGEM, 1, estacoes=[PAULISTA])
    assert 150 < d < 300


def test_limita_a_n_resultados():
    pares = mapas.estacoes_mais_proximas(*ORIGEM, 2, estacoes=[SE, IBIRAPUERA, PAULISTA])
    assert [e.id for e, _ in pares] == [1, 2]


def test_n_maior_que_o_total_devolve_todas():
    assert len(mapas.estacoes_mais_proximas(*ORIGEM, 10, estacoes=[SE, PAULISTA])) == 2


def test_n_zero_ou_negativo_devolve_vazio():
    assert mapas.estacoes_mais_proximas(*ORIGEM, 0, estacoes=[SE]) == []
    assert mapas.estacoes_mais_proximas(*ORIGEM, -1, estacoes=[SE]) == []


def test_sem_estacoes_devolve_vazio():
    assert mapas.estacoes_mais_proximas(*ORIGEM, 3, estacoes=[]) == []