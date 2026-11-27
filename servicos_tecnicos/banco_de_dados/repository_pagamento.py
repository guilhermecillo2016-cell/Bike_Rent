"""
servicos_tecnicos/banco_de_dados/repository_pagamento.py
-----------------------------------------------------------
Armazenamento em memória dos pagamentos (cobrança de uma corrida ou
compra de um pacote de minutos). Os cartões tokenizados ficam em
repository_cartao.py.

A regra "exatamente um entre locacao e pacote" é validada no
pagamento_service; aqui só se guarda.

`RepositorioPagamentoMemoria` implementa a interface `RepositorioPagamento`
([A13]). As funções de módulo continuam existindo como fachada da instância
padrão (`padrao`).
"""

from typing import Optional

from servicos_tecnicos.banco_de_dados import memoria
from servicos_tecnicos.banco_de_dados.enums import TipoPagamento
from servicos_tecnicos.banco_de_dados.repositorios import RepositorioPagamento
from dominio.locacao.locacao import Locacao
from dominio.pacote.pacote_minutos import PacoteMinutos
from dominio.pagamento.pagamento import Pagamento


class RepositorioPagamentoMemoria(memoria.ColecaoPorId, RepositorioPagamento):
    colecao = "pagamentos"
    atributo_id = "id_pagamento"

    def create(
        self,
        valor: float,
        tipo: TipoPagamento,
        locacao: Optional[Locacao] = None,
        pacote: Optional[PacoteMinutos] = None,
        token_cartao: Optional[str] = None,
    ) -> Pagamento:
        pagamento = Pagamento(
            valor, tipo,
            locacao=locacao, pacote=pacote, token_cartao=token_cartao,
            id_pagamento=memoria.proximo_id("pagamentos"),
        )
        return self.salvar(pagamento)


padrao = RepositorioPagamentoMemoria()


# --- Fachada de módulo (assinaturas de sempre) ---------------------------
def create(
    valor: float,
    tipo: TipoPagamento,
    locacao: Optional[Locacao] = None,
    pacote: Optional[PacoteMinutos] = None,
    token_cartao: Optional[str] = None,
) -> Pagamento:
    return padrao.create(valor, tipo, locacao, pacote, token_cartao)


def get_by_id(pagamento_id: int) -> Optional[Pagamento]:
    return padrao.get_by_id(pagamento_id)


def list_all() -> list[Pagamento]:
    return padrao.list_all()


def salvar(pagamento: Pagamento) -> Pagamento:
    return padrao.salvar(pagamento)
