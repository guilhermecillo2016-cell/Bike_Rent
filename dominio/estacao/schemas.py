"""
dominio/estacao/schemas.py
----------------------------
Schemas do domínio Estacao — História "Criar Estação" (2).
"""

from pydantic import BaseModel, Field


class EstacaoCreate(BaseModel):
    nome: str
    endereco: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    capacidade_total: int = Field(gt=0)


class EstacaoPublic(BaseModel):
    id: str
    nome: str
    endereco: str
    latitude: float
    longitude: float
    capacidade_total: int
    vagas_disponiveis: int
