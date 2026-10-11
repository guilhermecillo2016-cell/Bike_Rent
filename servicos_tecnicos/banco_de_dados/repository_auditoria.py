"""
servicos_tecnicos/banco_de_dados/repository_auditoria.py
-----------------------------------------------------------
Armazenamento em memória do histórico de auditoria: um evento a cada
alteração manual de status de bicicleta ou estação (UC2). Os eventos
só são acrescentados, nunca alterados.
"""

from datetime import datetime
from typing import Literal, Optional

from servicos_tecnicos.banco_de_dados import memoria
from servicos_tecnicos.banco_de_dados.models import EventoAuditoriaORM


def create(
        usuario_email: str,
        tipo_entidade: Literal["BICICLETA", "ESTACAO"],
        entidade_id: int,
        status_anterior: str,
        status_novo: str,
    ) -> EventoAuditoriaORM:
    auditoria = EventoAuditoriaORM(
        id=memoria.proximo_id("eventos_auditoria"),
        data_hora=datetime.now(),
        usuario_email=usuario_email,
        tipo_entidade=tipo_entidade,
        entidade_id=entidade_id,
        status_anterior=status_anterior,
        status_novo=status_novo,
    )
    memoria.eventos_auditoria[auditoria.id] = auditoria
    return auditoria


def get_by_id(auditoria_id: int) -> Optional[EventoAuditoriaORM]:
    return memoria.eventos_auditoria.get(auditoria_id)


def list_all() -> list[EventoAuditoriaORM]:
    return list(memoria.eventos_auditoria.values())