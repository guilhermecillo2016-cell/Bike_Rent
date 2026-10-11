"""
servicos_tecnicos/banco_de_dados/repository_pagamento.py
-----------------------------------------------------------
Armazenamento em memória dos pagamentos (cobrança de uma corrida ou
compra de um pacote de minutos). Os cartões tokenizados ficam em
repository_cartao.py.

A regra "exatamente um entre locacao_id e pacote_id" é validada no
pagamento_service; aqui só se guarda.
"""

from datetime import datetime
from typing import Optional

from servicos_tecnicos.banco_de_dados import memoria
from servicos_tecnicos.banco_de_dados.enums import TipoPagamento
from servicos_tecnicos.banco_de_dados.models import PagamentoORM


def create(
    valor: float,
    tipo: TipoPagamento,
    locacao_id: Optional[int] = None,
    pacote_id: Optional[int] = None,
    token_cartao: Optional[str] = None,
) -> PagamentoORM:
    pagamento = PagamentoORM(
        id=memoria.proximo_id("pagamentos"),
        valor=valor,
        tipo=tipo,
        data_hora=datetime.now(),
        locacao_id=locacao_id,
        pacote_id=pacote_id,
        token_cartao=token_cartao,
    )
    memoria.pagamentos[pagamento.id] = pagamento
    return pagamento


<<<<<<< HEAD
def list_cartoes(email_usuario: str) -> list[CartaoORM]:
    return memoria.cartoes.get(email_usuario, [])

def remover_cartao(email_usuario: str, cartao: CartaoORM) -> None:
    memoria.cartoes[email_usuario].remove(cartao)

def get_cartao(email_usuario: str, token: str) -> CartaoORM:
    for c in memoria.cartoes[email_usuario]:
        if c.token == token:
            return c
    return None
    
=======
def get_by_id(pagamento_id: int) -> Optional[PagamentoORM]:
    return memoria.pagamentos.get(pagamento_id)


def list_all() -> list[PagamentoORM]:
    return list(memoria.pagamentos.values())
>>>>>>> 6e6ce97598c03c997dad33ecb678be4de0305799
