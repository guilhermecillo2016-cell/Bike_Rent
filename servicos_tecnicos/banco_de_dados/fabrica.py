"""
servicos_tecnicos/banco_de_dados/fabrica.py
---------------------------------------------
Fábrica dos repositórios ([A13]): devolve o conjunto de repositórios que os
services usam. Por enquanto só existe a implementação em memória; a escolha
pela variável de ambiente `PERSISTENCIA` (memória ou PostgreSQL) entra na
[A16].

Uso nos services:

    from servicos_tecnicos.banco_de_dados.fabrica import repositorios
    repositorios().bicicleta.get_by_id(1)

`definir_repositorios(...)` troca o conjunto inteiro (outra implementação ou
dublês em testes); `definir_repositorios(None)` volta ao padrão em memória.
"""

from dataclasses import dataclass
from typing import Optional

from servicos_tecnicos.banco_de_dados.repositorios import (
    RepositorioAuditoria,
    RepositorioAvaria,
    RepositorioBicicleta,
    RepositorioCartao,
    RepositorioComprovante,
    RepositorioEstacao,
    RepositorioLocacao,
    RepositorioPacote,
    RepositorioPagamento,
    RepositorioUsuario,
)


@dataclass(frozen=True)
class Repositorios:
    """Um repositório de cada interface."""

    usuario: RepositorioUsuario
    estacao: RepositorioEstacao
    bicicleta: RepositorioBicicleta
    locacao: RepositorioLocacao
    pacote: RepositorioPacote
    pagamento: RepositorioPagamento
    cartao: RepositorioCartao
    avaria: RepositorioAvaria
    comprovante: RepositorioComprovante
    auditoria: RepositorioAuditoria


def repositorios_em_memoria() -> Repositorios:
    """As instâncias padrão em memória (as mesmas que as funções de módulo
    `repository_*.py` usam, então os dois caminhos veem os mesmos dados)."""
    from servicos_tecnicos.banco_de_dados import (
        repository_auditoria,
        repository_avaria,
        repository_bicicleta,
        repository_cartao,
        repository_comprovante,
        repository_estacao,
        repository_locacao,
        repository_pacote,
        repository_pagamento,
        repository_usuario,
    )

    return Repositorios(
        usuario=repository_usuario.padrao,
        estacao=repository_estacao.padrao,
        bicicleta=repository_bicicleta.padrao,
        locacao=repository_locacao.padrao,
        pacote=repository_pacote.padrao,
        pagamento=repository_pagamento.padrao,
        cartao=repository_cartao.padrao,
        avaria=repository_avaria.padrao,
        comprovante=repository_comprovante.padrao,
        auditoria=repository_auditoria.padrao,
    )


_atual: Optional[Repositorios] = None


def repositorios() -> Repositorios:
    """O conjunto em uso (padrão: memória, criado na primeira chamada)."""
    global _atual
    if _atual is None:
        _atual = repositorios_em_memoria()
    return _atual


def definir_repositorios(conjunto: Optional[Repositorios]) -> None:
    """Troca o conjunto em uso; None volta ao padrão em memória."""
    global _atual
    _atual = conjunto
