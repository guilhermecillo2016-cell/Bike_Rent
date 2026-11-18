"""
servicos_tecnicos/banco_de_dados/repository_pacote.py
-----------------------------------------------------------
Armazenamento em memória dos pacotes de minutos pré-pagos. O pacote
nasce inativo e só é ativado pelo service depois que o pagamento da
compra é aprovado.
"""

from datetime import datetime
from typing import Optional

from servicos_tecnicos.banco_de_dados import memoria
from dominio.pacote.pacote_minutos import PacoteMinutos
from dominio.usuario.usuario import Usuario


def create(
    usuario: Usuario,
    minutos_totais: int,
    data_validade: datetime,
) -> PacoteMinutos:
    pacote = PacoteMinutos(
        minutos_totais, data_validade,
        usuario=usuario, id_pacote=memoria.proximo_id("pacotes"),
    )
    memoria.pacotes[pacote.id_pacote] = pacote
    return pacote


def get_by_id(pacote_id: int) -> Optional[PacoteMinutos]:
    return memoria.pacotes.get(pacote_id)


def list_all() -> list[PacoteMinutos]:
    return list(memoria.pacotes.values())


def list_by_email(usuario_email: str) -> list[PacoteMinutos]:
    return [p for p in memoria.pacotes.values() if p.usuario_email == usuario_email]
