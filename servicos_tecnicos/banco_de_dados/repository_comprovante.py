"""
servicos_tecnicos/banco_de_dados/repository_comprovante.py
-----------------------------------------------------------
Armazenamento em memória dos comprovantes digitais de viagem, um por
locação encerrada. Nunca guarda dados sensíveis de cartão.
"""

from typing import Optional

from servicos_tecnicos.banco_de_dados import memoria
from dominio.comprovante.comprovante_viagem import ComprovanteViagem
from dominio.locacao.locacao import Locacao
from dominio.pagamento.pagamento import Pagamento


def create(
    locacao: Locacao,
    pagamento: Optional[Pagamento] = None,
) -> ComprovanteViagem:
    comprovante = ComprovanteViagem(
        locacao, pagamento,
        id_comprovante=memoria.proximo_id("comprovantes"),
    )
    memoria.comprovantes[comprovante.id_comprovante] = comprovante
    return comprovante


def get_by_id(comprovante_id: int) -> Optional[ComprovanteViagem]:
    return memoria.comprovantes.get(comprovante_id)


def list_all() -> list[ComprovanteViagem]:
    return list(memoria.comprovantes.values())


def get_by_locacao(locacao_id: int) -> Optional[ComprovanteViagem]:
    return next((c for c in memoria.comprovantes.values() if c.locacao_id == locacao_id), None)
