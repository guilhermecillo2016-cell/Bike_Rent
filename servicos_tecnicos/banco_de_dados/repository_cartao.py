"""
servicos_tecnicos/banco_de_dados/repository_cartao.py
-----------------------------------------------------------
Armazenamento em memória dos cartões (métodos de pagamento tokenizados) de
cada usuário. Nunca guarda número completo de cartão nem CVV —
apenas o que o tokenizador devolve (token, bandeira, últimos 4
dígitos).
"""

from servicos_tecnicos.banco_de_dados import memoria
from servicos_tecnicos.banco_de_dados.models import CartaoORM


def add_cartao(email_usuario: str, cartao: CartaoORM) -> CartaoORM:
    memoria.cartoes.setdefault(email_usuario, []).append(cartao)
    return cartao


def list_cartoes(email_usuario: str) -> list[CartaoORM]:
    return memoria.cartoes.get(email_usuario, [])


def remover_cartao(email_usuario: str, cartao: CartaoORM) -> None:
    memoria.cartoes[email_usuario].remove(cartao)


def get_cartao(email_usuario: str, token: str) -> CartaoORM:
    for c in memoria.cartoes[email_usuario]:
        if c.token == token:
            return c
    return None