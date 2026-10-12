"""
dominio/auditoria/service.py
------------------------------
Histórico de auditoria (UC2): um evento a cada alteração manual de
status de bicicleta ou estação. Quem altera o status chama registrar();
a rota do administrador usa listar().
"""

from typing import Literal

from dominio.auditoria.schemas import EventoAuditoriaPublic
from servicos_tecnicos.banco_de_dados import repository_auditoria as repo
from servicos_tecnicos.banco_de_dados.models import EventoAuditoriaORM


def to_public(evento: EventoAuditoriaORM) -> EventoAuditoriaPublic:
    return EventoAuditoriaPublic(
        id=evento.id,
        usuario_email=evento.usuario_email,
        tipo_entidade=evento.tipo_entidade,
        entidade_id=evento.entidade_id,
        status_anterior=evento.status_anterior,
        status_novo=evento.status_novo,
        data_hora=evento.data_hora,
    )


def registrar(
    usuario_email: str,
    tipo_entidade: Literal["BICICLETA", "ESTACAO"],
    entidade_id: int,
    status_anterior: str,
    status_novo: str,
) -> EventoAuditoriaORM:
    """Grava um evento de alteração de status."""
    return repo.create(
        usuario_email, tipo_entidade, entidade_id, status_anterior, status_novo
    )


def listar() -> list[EventoAuditoriaORM]:
    """Todos os eventos, do mais recente para o mais antigo."""
    return sorted(repo.list_all(), key=lambda e: e.id, reverse=True)
