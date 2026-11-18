"""
servicos_tecnicos/banco_de_dados/repository_cartao.py
-----------------------------------------------------------
Armazenamento em memória dos cartões (métodos de pagamento tokenizados) de
cada usuário. Nunca guarda número completo de cartão nem CVV —
apenas o que o tokenizador devolve (token, bandeira, últimos 4
dígitos).
"""

from servicos_tecnicos.banco_de_dados import memoria
from dominio.pagamento.cartao import Cartao


def add_cartao(email_usuario: str, cartao: Cartao) -> Cartao:
    memoria.cartoes.setdefault(email_usuario, []).append(cartao)
    return cartao


def list_cartoes(email_usuario: str) -> list[Cartao]:
    return memoria.cartoes.get(email_usuario, [])


def remover_cartao(email_usuario: str, cartao: Cartao) -> None:
    memoria.cartoes[email_usuario].remove(cartao)


def get_cartao(email_usuario: str, token: str) -> Cartao:
    for c in memoria.cartoes[email_usuario]:
        if c.token == token:
            return c
    return None

def get_credito_by_email(email_usuario: str) -> Cartao:
    """Retorna o cartão de crédito do usuário, ou None se não houver."""
    for c in memoria.cartoes.get(email_usuario, []):
        if c.tipo == "CARTAO_CREDITO":
            return c
    return None


def get_debito_by_email(email_usuario: str) -> Cartao:
    """Retorna o cartão de débito do usuário, ou None se não houver."""
    for c in memoria.cartoes.get(email_usuario, []):
        if c.tipo == "CARTAO_DEBITO":
            return c
    return None
