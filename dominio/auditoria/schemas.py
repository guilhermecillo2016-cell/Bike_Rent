"""
dominio/auditoria/schemas.py
------------------------------
Schema do histórico de auditoria (UC2): como cada evento de alteração
manual de status sai pela API.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class EventoAuditoriaPublic(BaseModel):
    id: int
    data_hora: datetime
    usuario_email: str
    tipo_entidade: Literal["BICICLETA", "ESTACAO"]
    entidade_id: int
    status_anterior: str
    status_novo: str
