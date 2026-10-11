"""
servicos_tecnicos/banco_de_dados/repository_bicicleta.py
-----------------------------------------------------------
Armazenamento em memória das bicicletas. A localização de uma
bicicleta é só o seu estacao_id: a estação não guarda lista nenhuma,
a lista (e a contagem de vagas) sai de uma consulta por estacao_id.
"""

import uuid
from typing import Optional

from servicos_tecnicos.banco_de_dados import memoria
from servicos_tecnicos.banco_de_dados.models import BicicletaORM


def _novo_qr_code() -> str:
    """Código aleatório (não dá para adivinhar a partir do id) e único."""
    while True:
        qr_code = "BIKE-" + uuid.uuid4().hex[:12].upper()
        if get_by_qr(qr_code) is None:
            return qr_code


def create(estacao_id: int) -> BicicletaORM:
    bicicleta = BicicletaORM(
        id=memoria.proximo_id("bicicletas"),
        qr_code=_novo_qr_code(),
        estacao_id=estacao_id,
    )
    memoria.bicicletas[bicicleta.id] = bicicleta
    return bicicleta


def get_by_id(bicicleta_id: int) -> Optional[BicicletaORM]:
    return memoria.bicicletas.get(bicicleta_id)


def get_by_qr(qr_code: str) -> Optional[BicicletaORM]:
    return next((b for b in memoria.bicicletas.values() if b.qr_code == qr_code), None)


def list_all() -> list[BicicletaORM]:
    return list(memoria.bicicletas.values())


def list_by_estacao(estacao_id: int) -> list[BicicletaORM]:
    return [b for b in memoria.bicicletas.values() if b.estacao_id == estacao_id]
