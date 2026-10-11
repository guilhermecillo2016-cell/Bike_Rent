"""
servicos_tecnicos/banco_de_dados/repository_locacao.py
-----------------------------------------------------------
Armazenamento em memória das locações (corridas). Regras como "uma
corrida ativa por ciclista" ficam no service; aqui só se guarda.
"""

from datetime import datetime
from typing import Optional

from servicos_tecnicos.banco_de_dados import memoria
from servicos_tecnicos.banco_de_dados.models import LocacaoORM


def create(
    usuario_email: str,
    bicicleta_id: int,
    estacao_origem_id: int,
) -> LocacaoORM:
    locacao = LocacaoORM(
        id=memoria.proximo_id("locacoes"),
        usuario_email=usuario_email,
        bicicleta_id=bicicleta_id,
        estacao_origem_id=estacao_origem_id,
        data_hora_inicio=datetime.now(),
    )
    memoria.locacoes[locacao.id] = locacao
    return locacao


def get_by_id(locacao_id: int) -> Optional[LocacaoORM]:
    return memoria.locacoes.get(locacao_id)


def list_all() -> list[LocacaoORM]:
    return list(memoria.locacoes.values())
