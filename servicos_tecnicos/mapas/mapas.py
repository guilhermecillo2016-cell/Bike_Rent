"""Serviço técnico de mapas (simulado, sem rede): estações mais próximas."""

from dominio.geolocalizacao.geolocalizacao import Geolocalizacao
from servicos_tecnicos.banco_de_dados import memoria


def _localizacao(estacao) -> Geolocalizacao:
    # SUPOSIÇÃO: a estação guarda `latitude` e `longitude` como atributos.
    return Geolocalizacao(estacao.latitude, estacao.longitude)


def estacoes_mais_proximas(lat: float, lng: float, n: int, estacoes=None):
    """As `n` estações mais próximas de (lat, lng), da mais perto para a mais longe.

    Devolve uma lista de pares (estacao, distancia_em_metros). Se `estacoes` não
    for informado, usa todas as estações da memória. Quem chama decide quais
    estações são elegíveis (ex.: sem as BLOQUEADAS) e passa a lista já filtrada.
    """
    if n <= 0:
        return []
    if estacoes is None:
        estacoes = list(memoria.estacoes.values())
    origem = Geolocalizacao(lat, lng)
    pares = [(e, origem.calcular_distancia_em_metros(_localizacao(e))) for e in estacoes]
    pares.sort(key=lambda par: par[1])
    return pares[:n]