"""
servicos_tecnicos/banco_de_dados/repository_bicicleta.py
-----------------------------------------------------------
Armazenamento em memória das bicicletas. A localização de uma
bicicleta é só o seu estacao_id: a estação não guarda lista nenhuma,
a lista (e a contagem de vagas) sai de uma consulta por estacao_id.
"""

from typing import Optional

from servicos_tecnicos.banco_de_dados import memoria
from servicos_tecnicos.banco_de_dados.models import BicicletaORM


def get_by_id(bicicleta_id: int) -> Optional[BicicletaORM]:
    return memoria.bicicletas.get(bicicleta_id)


def list_all() -> list[BicicletaORM]:
    return list(memoria.bicicletas.values())


def list_by_estacao(estacao_id: int) -> list[BicicletaORM]:
    return [b for b in memoria.bicicletas.values() if b.estacao_id == estacao_id]
