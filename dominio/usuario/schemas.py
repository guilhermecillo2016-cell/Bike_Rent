"""
dominio/usuario/schemas.py
----------------------------
Schemas (formato dos dados) do domínio Usuario — Histórias:
"Cadastrar" (1) e base para "Vincular Método de Pagamento" (3),
já que essa história exige um ciclista autenticado.
"""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UsuarioCreate(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=6)
    cpf: str
    telefone: str
    endereco: Optional[str] = None


class UsuarioPublic(BaseModel):
    email: EmailStr
    cpf: str  # sempre mascarado antes de sair pela API — ver service.mask_cpf
    telefone: str
    endereco: Optional[str] = None
    is_admin: bool = False


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: Optional[str] = None
