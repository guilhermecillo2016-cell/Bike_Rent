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


class AdminCreate(BaseModel):
    """Cadastro de administrador — só o essencial (Pessoa: nome/email/senha).
    Sem CPF/telefone: administrador não é um ciclista."""

    email: EmailStr
    senha: str = Field(min_length=6)


class UsuarioPublic(BaseModel):
    email: EmailStr
    cpf: Optional[str] = None  # sempre mascarado antes de sair pela API — ver service.mask_cpf
    telefone: Optional[str] = None
    endereco: Optional[str] = None
    is_admin: bool = False


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: Optional[str] = None
