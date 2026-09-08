"""
servicos_tecnicos/banco_de_dados/repository_estacao.py
-----------------------------------------------------------
Armazenamento em memória das estações cadastradas pelo administrador.
"""

import uuid
from typing import Optional

from servicos_tecnicos.banco_de_dados import memoria
from servicos_tecnicos.banco_de_dados.models import EstacaoORM


def create(nome: str, endereco: str, latitude: float, longitude: float, capacidade_total: int) -> EstacaoORM:
    estacao = EstacaoORM(
        id=uuid.uuid4().hex[:8],
        nome=nome,
        endereco=endereco,
        latitude=latitude,
        longitude=longitude,
        capacidade_total=capacidade_total,
        vagas_disponiveis=capacidade_total,
    )
    memoria.estacoes[estacao.id] = estacao
    return estacao


def list_all() -> list[EstacaoORM]:
    return list(memoria.estacoes.values())


def get_by_id(estacao_id: str) -> Optional[EstacaoORM]:
    return memoria.estacoes.get(estacao_id)
