"""
dominio/pagamento/cartao.py
-----------------------------------
Classe `Cartao` do diagrama: cartão tokenizado do usuário.
Nunca guarda número completo nem CVV.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Cartao:
    token: str
    ultimos_digitos: str
    bandeira: str
    nome_titular: str
    validade: str
    tipo: str
    apelido: Optional[str] = None
