"""
servicos_tecnicos/banco_de_dados/repository_pacote.py
-----------------------------------------------------------
Armazenamento em memória dos pacotes de minutos pré-pagos. O pacote
nasce inativo e só é ativado pelo service depois que o pagamento da
compra é aprovado.

`RepositorioPacoteMemoria` implementa a interface `RepositorioPacote`
([A13]). As funções de módulo continuam existindo como fachada da instância
padrão (`padrao`).
"""

from datetime import datetime
from typing import Optional

from servicos_tecnicos.banco_de_dados import memoria
from servicos_tecnicos.banco_de_dados.repositorios import RepositorioPacote
from dominio.pacote.pacote_minutos import PacoteMinutos
from dominio.usuario.usuario import Usuario


class RepositorioPacoteMemoria(memoria.ColecaoPorId, RepositorioPacote):
    colecao = "pacotes"
    atributo_id = "id_pacote"

    def create(self, usuario: Usuario, minutos_totais: int, data_validade: datetime) -> PacoteMinutos:
        pacote = PacoteMinutos(
            minutos_totais, data_validade,
            usuario=usuario, id_pacote=memoria.proximo_id("pacotes"),
        )
        return self.salvar(pacote)

    def list_by_email(self, usuario_email: str) -> list[PacoteMinutos]:
        return [p for p in self.list_all() if p.usuario_email == usuario_email]


padrao = RepositorioPacoteMemoria()


# --- Fachada de módulo (assinaturas de sempre) ---------------------------
def create(
    usuario: Usuario,
    minutos_totais: int,
    data_validade: datetime,
) -> PacoteMinutos:
    return padrao.create(usuario, minutos_totais, data_validade)


def get_by_id(pacote_id: int) -> Optional[PacoteMinutos]:
    return padrao.get_by_id(pacote_id)


def list_all() -> list[PacoteMinutos]:
    return padrao.list_all()


def list_by_email(usuario_email: str) -> list[PacoteMinutos]:
    return padrao.list_by_email(usuario_email)


def salvar(pacote: PacoteMinutos) -> PacoteMinutos:
    return padrao.salvar(pacote)
