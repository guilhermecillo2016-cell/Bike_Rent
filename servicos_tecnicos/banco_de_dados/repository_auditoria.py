"""
servicos_tecnicos/banco_de_dados/repository_auditoria.py
-----------------------------------------------------------
Armazenamento em memória do histórico de auditoria: um evento a cada
alteração manual de status de bicicleta ou estação (UC2). Os eventos
só são acrescentados, nunca alterados.

`RepositorioAuditoriaMemoria` implementa a interface `RepositorioAuditoria`
([A13]). As funções de módulo continuam existindo como fachada da instância
padrão (`padrao`).
"""

from datetime import datetime
from typing import Literal, Optional

from servicos_tecnicos.banco_de_dados import memoria
from servicos_tecnicos.banco_de_dados.repositorios import RepositorioAuditoria
from dominio.auditoria.evento_auditoria import EventoAuditoria


class RepositorioAuditoriaMemoria(memoria.ColecaoPorId, RepositorioAuditoria):
    colecao = "eventos_auditoria"
    atributo_id = "id"

    def create(
        self,
        usuario_email: str,
        tipo_entidade: Literal["BICICLETA", "ESTACAO"],
        entidade_id: int,
        status_anterior: str,
        status_novo: str,
    ) -> EventoAuditoria:
        auditoria = EventoAuditoria(
            id=memoria.proximo_id("eventos_auditoria"),
            data_hora=datetime.now(),
            usuario_email=usuario_email,
            tipo_entidade=tipo_entidade,
            entidade_id=entidade_id,
            status_anterior=status_anterior,
            status_novo=status_novo,
        )
        return self.salvar(auditoria)


padrao = RepositorioAuditoriaMemoria()


# --- Fachada de módulo (assinaturas de sempre) ---------------------------
def create(
        usuario_email: str,
        tipo_entidade: Literal["BICICLETA", "ESTACAO"],
        entidade_id: int,
        status_anterior: str,
        status_novo: str,
    ) -> EventoAuditoria:
    return padrao.create(
        usuario_email, tipo_entidade, entidade_id, status_anterior, status_novo
    )


def get_by_id(auditoria_id: int) -> Optional[EventoAuditoria]:
    return padrao.get_by_id(auditoria_id)


def list_all() -> list[EventoAuditoria]:
    return padrao.list_all()


def salvar(evento: EventoAuditoria) -> EventoAuditoria:
    return padrao.salvar(evento)
