"""
servicos_tecnicos/banco_de_dados/repository_estacao.py
-----------------------------------------------------------
Armazenamento em memória das estações cadastradas pelo administrador.
"""

from typing import Optional

from dominio.geolocalizacao.geolocalizacao import Geolocalizacao
from servicos_tecnicos.banco_de_dados import memoria
from dominio.estacao.estacao import Estacao


def create(nome: str, endereco: str, latitude: float, longitude: float, capacidade_total: int) -> Estacao:
    estacao = Estacao(
        id=memoria.proximo_id("estacoes"),
        nome=nome,
        endereco=endereco,
        localizacao=Geolocalizacao(latitude, longitude),
        capacidade_total=capacidade_total,
    )
    memoria.estacoes[estacao.id] = estacao
    return estacao


def list_all() -> list[Estacao]:
    return list(memoria.estacoes.values())


def get_by_id(estacao_id: int) -> Optional[Estacao]:
    return memoria.estacoes.get(estacao_id)
