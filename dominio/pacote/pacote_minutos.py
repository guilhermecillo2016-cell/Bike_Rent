"""
dominio/pacote/pacote_minutos.py
----------------------------------------
Classe `PacoteMinutos` do diagrama: pacote de minutos comprado pelo usuário.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class PacoteMinutos:
    id: int
    usuario_email: str
    minutos_totais: int
    minutos_restantes: int
    data_validade: datetime
    # False até o pagamento da compra ser aprovado
    ativo: bool = False
