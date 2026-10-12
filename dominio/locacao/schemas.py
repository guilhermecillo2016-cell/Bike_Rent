"""
dominio/locacao/schemas.py
----------------------------
Schemas do domínio Locacao — início de corrida (B3).
"""

from datetime import datetime
from pydantic import BaseModel, Field


class LocacaoCreate(BaseModel):
    qr_code: str = Field(min_length=1)


class LocacaoPublic(BaseModel):
    id: int
    bicicleta_id: int
    estacao_origem_id: int
    data_hora_inicio: datetime
    em_andamento: bool