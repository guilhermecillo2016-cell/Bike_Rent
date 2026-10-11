"""
servicos_tecnicos/banco_de_dados/repository_comprovante.py
-----------------------------------------------------------
Armazenamento em memória dos comprovantes digitais de viagem, um por
locação encerrada. Nunca guarda dados sensíveis de cartão.
"""

from datetime import datetime
from typing import Optional

from servicos_tecnicos.banco_de_dados import memoria
from servicos_tecnicos.banco_de_dados.models import ComprovanteORM


def create(
    resumo_trajeto: str,
    tarifa_aplicada: float,
    locacao_id: int,
    pagamento_id: Optional[int] = None,
) -> ComprovanteORM:
    comprovante = ComprovanteORM(
        id=memoria.proximo_id("comprovantes"),
        data_emissao=datetime.now(),
        resumo_trajeto=resumo_trajeto,
        tarifa_aplicada=tarifa_aplicada,
        locacao_id=locacao_id,
        pagamento_id=pagamento_id,
    )
    memoria.comprovantes[comprovante.id] = comprovante
    return comprovante


def get_by_id(comprovante_id: int) -> Optional[ComprovanteORM]:
    return memoria.comprovantes.get(comprovante_id)


def list_all() -> list[ComprovanteORM]:
    return list(memoria.comprovantes.values())


def get_by_locacao(locacao_id: int) -> Optional[ComprovanteORM]:
    return next((c for c in memoria.comprovantes.values() if c.locacao_id == locacao_id), None)
