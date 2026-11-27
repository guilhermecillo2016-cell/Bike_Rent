"""
servicos_tecnicos/banco_de_dados/repository_cartao.py
-----------------------------------------------------------
Armazenamento em memória dos cartões (métodos de pagamento tokenizados) de
cada usuário. Nunca guarda número completo de cartão nem CVV —
apenas o que o tokenizador devolve (token, bandeira, últimos 4
dígitos).

`RepositorioCartaoMemoria` implementa a interface `RepositorioCartao`
([A13]). As funções de módulo continuam existindo como fachada da instância
padrão (`padrao`). Os cartões ficam agrupados por e-mail do dono até a [C15]
ligar Cartao ao Usuario por objeto; o token identifica o cartão até a [A23]
trazer `id_cartao`.
"""

from typing import Optional

from servicos_tecnicos.banco_de_dados import memoria
from servicos_tecnicos.banco_de_dados.repositorios import RepositorioCartao
from dominio.pagamento.cartao import Cartao


class RepositorioCartaoMemoria(RepositorioCartao):

    def add_cartao(self, email_usuario: str, cartao: Cartao) -> Cartao:
        memoria.cartoes.setdefault(email_usuario, []).append(cartao)
        return cartao

    def list_cartoes(self, email_usuario: str) -> list[Cartao]:
        return memoria.cartoes.get(email_usuario, [])

    def remover_cartao(self, email_usuario: str, cartao: Cartao) -> None:
        memoria.cartoes[email_usuario].remove(cartao)

    def get_cartao(self, email_usuario: str, token: str) -> Optional[Cartao]:
        for c in memoria.cartoes[email_usuario]:
            if c.token == token:
                return c
        return None

    def _do_tipo(self, email_usuario: str, tipo: str) -> Optional[Cartao]:
        for c in memoria.cartoes.get(email_usuario, []):
            if c.tipo == tipo:
                return c
        return None

    def get_credito_by_email(self, email_usuario: str) -> Optional[Cartao]:
        """Retorna o cartão de crédito do usuário, ou None se não houver."""
        return self._do_tipo(email_usuario, "CARTAO_CREDITO")

    def get_debito_by_email(self, email_usuario: str) -> Optional[Cartao]:
        """Retorna o cartão de débito do usuário, ou None se não houver."""
        return self._do_tipo(email_usuario, "CARTAO_DEBITO")

    def list_all(self) -> list[Cartao]:
        return [c for cartoes in memoria.cartoes.values() for c in cartoes]

    def salvar(self, cartao: Cartao) -> Cartao:
        """Atualiza um cartão já vinculado (achado pelo token). Para vincular
        um cartão novo use `add_cartao`, que precisa do dono."""
        for cartoes in memoria.cartoes.values():
            for i, c in enumerate(cartoes):
                if c.token == cartao.token:
                    cartoes[i] = cartao
                    return cartao
        raise ValueError("Cartão não vinculado a nenhum usuário; use add_cartao")


padrao = RepositorioCartaoMemoria()


# --- Fachada de módulo (assinaturas de sempre) ---------------------------
def add_cartao(email_usuario: str, cartao: Cartao) -> Cartao:
    return padrao.add_cartao(email_usuario, cartao)


def list_cartoes(email_usuario: str) -> list[Cartao]:
    return padrao.list_cartoes(email_usuario)


def remover_cartao(email_usuario: str, cartao: Cartao) -> None:
    padrao.remover_cartao(email_usuario, cartao)


def get_cartao(email_usuario: str, token: str) -> Cartao:
    return padrao.get_cartao(email_usuario, token)


def get_credito_by_email(email_usuario: str) -> Cartao:
    """Retorna o cartão de crédito do usuário, ou None se não houver."""
    return padrao.get_credito_by_email(email_usuario)


def get_debito_by_email(email_usuario: str) -> Cartao:
    """Retorna o cartão de débito do usuário, ou None se não houver."""
    return padrao.get_debito_by_email(email_usuario)


def list_all() -> list[Cartao]:
    return padrao.list_all()


def salvar(cartao: Cartao) -> Cartao:
    return padrao.salvar(cartao)
