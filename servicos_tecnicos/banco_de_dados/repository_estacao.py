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
        memoria.proximo_id("estacoes"), nome, endereco, capacidade_total,
        localizacao=Geolocalizacao(latitude, longitude),
    )
    memoria.estacoes[estacao.id_estacao] = estacao
    return estacao


def list_all() -> list[Estacao]:
    return list(memoria.estacoes.values())


def get_by_id(estacao_id: int) -> Optional[Estacao]:
    return memoria.estacoes.get(estacao_id)
