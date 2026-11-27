"""
servicos_tecnicos/banco_de_dados/repository_comprovante.py
-----------------------------------------------------------
Armazenamento em memória dos comprovantes digitais de viagem, um por
locação encerrada. Nunca guarda dados sensíveis de cartão.

`RepositorioComprovanteMemoria` implementa a interface
`RepositorioComprovante` ([A13]). As funções de módulo continuam existindo
como fachada da instância padrão (`padrao`).
"""

from typing import Optional

from servicos_tecnicos.banco_de_dados import memoria
from servicos_tecnicos.banco_de_dados.repositorios import RepositorioComprovante
from dominio.comprovante.comprovante_viagem import ComprovanteViagem
from dominio.locacao.locacao import Locacao
from dominio.pagamento.pagamento import Pagamento


class RepositorioComprovanteMemoria(memoria.ColecaoPorId, RepositorioComprovante):
    colecao = "comprovantes"
    atributo_id = "id_comprovante"

    def create(self, locacao: Locacao, pagamento: Optional[Pagamento] = None) -> ComprovanteViagem:
        comprovante = ComprovanteViagem(
            locacao, pagamento,
            id_comprovante=memoria.proximo_id("comprovantes"),
        )
        return self.salvar(comprovante)

    def get_by_locacao(self, locacao_id: int) -> Optional[ComprovanteViagem]:
        return next((c for c in self.list_all() if c.locacao_id == locacao_id), None)


padrao = RepositorioComprovanteMemoria()


# --- Fachada de módulo (assinaturas de sempre) ---------------------------
def create(
    locacao: Locacao,
    pagamento: Optional[Pagamento] = None,
) -> ComprovanteViagem:
    return padrao.create(locacao, pagamento)


def get_by_id(comprovante_id: int) -> Optional[ComprovanteViagem]:
    return padrao.get_by_id(comprovante_id)


def list_all() -> list[ComprovanteViagem]:
    return padrao.list_all()


def get_by_locacao(locacao_id: int) -> Optional[ComprovanteViagem]:
    return padrao.get_by_locacao(locacao_id)


def salvar(comprovante: ComprovanteViagem) -> ComprovanteViagem:
    return padrao.salvar(comprovante)
