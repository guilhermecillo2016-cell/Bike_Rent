"""
dominio/auditoria/evento_auditoria.py
---------------------------------------------
Classe `EventoAuditoria`: histórico de alterações manuais de status.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass
class EventoAuditoria:
    """Histórico de alterações manuais de status (UC2, pós-condição 3).
    Não consta no diagrama de classes; ver issue [C7]."""

    id: int
    data_hora: datetime
    usuario_email: str
    tipo_entidade: Literal["BICICLETA", "ESTACAO"]
    entidade_id: int
    status_anterior: str
    status_novo: str
