"""
dominio/pagamento/schemas.py
------------------------------
Schemas do domínio Pagamento — História "Vincular Método de
Pagamento" (3).

CartaoCreate é o que o cliente envia (inclui dados sensíveis que
nunca são armazenados). CartaoPublic é o que a API devolve/lista —
só dados tokenizados e não sensíveis.
"""

from typing import Optional
from pydantic import BaseModel, Field


class CartaoCreate(BaseModel):
    numero_cartao: str = Field(min_length=12, max_length=19)
    nome_titular: str
    validade: str = Field(pattern=r"^\d{2}/\d{2}$", description="Formato MM/AA")
    cvv: str = Field(min_length=3, max_length=4)
    apelido: Optional[str] = None


class CartaoPublic(BaseModel):
    token: str
    bandeira: str
    ultimos_digitos: str
    nome_titular: str
    validade: str
    apelido: Optional[str] = None
