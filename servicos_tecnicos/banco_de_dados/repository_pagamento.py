"""
servicos_tecnicos/banco_de_dados/repository_pagamento.py
-----------------------------------------------------------
Armazenamento em memória dos pagamentos (cobrança de uma corrida ou
compra de um pacote de minutos). Os cartões tokenizados ficam em
repository_cartao.py.

A regra "exatamente um entre locacao e pacote" é validada no
pagamento_service; aqui só se guarda.
"""

from typing import Optional

from servicos_tecnicos.banco_de_dados import memoria
from servicos_tecnicos.banco_de_dados.enums import TipoPagamento
from dominio.locacao.locacao import Locacao
from dominio.pacote.pacote_minutos import PacoteMinutos
from dominio.pagamento.pagamento import Pagamento


def create(
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
    memoria.pagamentos[pagamento.id_pagamento] = pagamento
    return pagamento


def get_by_id(pagamento_id: int) -> Optional[Pagamento]:
    return memoria.pagamentos.get(pagamento_id)


def list_all() -> list[Pagamento]:
    return list(memoria.pagamentos.values())

