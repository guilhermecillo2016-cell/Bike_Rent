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

class LocacaoAndamento(BaseModel):
    locacao_id: int
    bicicleta_id: int
    estacao_origem_id: int
    estacao_origem_nome: str
    data_hora_inicio: datetime
    duracao_segundos: int
    duracao_minutos: int          # minutos iniciados (teto), base da tarifa
    minutos_pacote: int           # quanto do saldo do pacote cobriria a corrida
    custo_estimado: float         # só o excedente, já descontado o pacote