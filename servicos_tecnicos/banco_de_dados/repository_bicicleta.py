"""
servicos_tecnicos/banco_de_dados/repository_bicicleta.py
-----------------------------------------------------------
Armazenamento em memória das bicicletas. Quem guarda a lista das
bicicletas de cada estação é a própria Estacao (fonte da verdade);
Bicicleta.estacao_id só espelha essa associação.
"""

import uuid
from typing import Optional

from servicos_tecnicos.banco_de_dados import memoria
from dominio.bicicleta.bicicleta import Bicicleta
from dominio.estacao.estacao import Estacao


def _novo_qr_code() -> str:
    """Código aleatório (não dá para adivinhar a partir do id) e único."""
    while True:
        qr_code = "BIKE-" + uuid.uuid4().hex[:12].upper()
        if get_by_qr(qr_code) is None:
            return qr_code


def create(estacao: Optional[Estacao]) -> Bicicleta:
    """Cria a bicicleta já estacionada em `estacao` (ou solta, se None)."""
    bicicleta = Bicicleta(memoria.proximo_id("bicicletas"), _novo_qr_code())
    memoria.bicicletas[bicicleta.id_bicicleta] = bicicleta
    if estacao is not None:
        estacao.adicionar_bicicleta(bicicleta)
    return bicicleta


def get_by_id(bicicleta_id: int) -> Optional[Bicicleta]:
    return memoria.bicicletas.get(bicicleta_id)


def get_by_qr(qr_code: str) -> Optional[Bicicleta]:
    return next((b for b in memoria.bicicletas.values() if b.qr_code == qr_code), None)


def list_all() -> list[Bicicleta]:
    return list(memoria.bicicletas.values())


def list_by_estacao(estacao_id: int) -> list[Bicicleta]:
    """Quem sabe quais bicicletas estão na estação é a própria Estacao;
    aqui só se pergunta a ela (na ordem de cadastro, como sempre)."""
    estacao = memoria.estacoes.get(estacao_id)
    if estacao is None:
        return []
    return sorted(estacao.bicicletas, key=lambda b: b.id)
