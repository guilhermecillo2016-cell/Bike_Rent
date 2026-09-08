"""
dominio/pagamento/service.py
------------------------------
Regras de negócio do domínio Pagamento: validação dos dados do
cartão (Luhn, validade) e vínculo com o usuário autenticado, delegando
a tokenização ao serviço técnico correspondente.
"""

import re
from datetime import datetime

from fastapi import HTTPException, status

from servicos_tecnicos.pagamentos import tokenizador
from servicos_tecnicos.banco_de_dados import repository_pagamento as repo
from servicos_tecnicos.banco_de_dados.models import CartaoORM
from dominio.pagamento.schemas import CartaoCreate


def _numero_valido_luhn(numero_cartao: str) -> bool:
    """Algoritmo de Luhn: validação padrão de números de cartão."""
    digitos = re.sub(r"\D", "", numero_cartao)
    soma = 0
    for i, char in enumerate(reversed(digitos)):
        n = int(char)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        soma += n
    return soma % 10 == 0


def _validade_no_futuro(validade: str) -> bool:
    """validade no formato MM/AA — verifica se ainda não expirou."""
    try:
        mes, ano = validade.split("/")
        mes, ano = int(mes), 2000 + int(ano)
        if not 1 <= mes <= 12:
            return False
        ultimo_dia_mes = datetime(ano, mes % 12 + 1, 1) if mes < 12 else datetime(ano + 1, 1, 1)
        return ultimo_dia_mes > datetime.now()
    except (ValueError, IndexError):
        return False


def vincular_cartao(email_usuario: str, dados: CartaoCreate) -> CartaoORM:
    """"if not _numero_valido_luhn(dados.numero_cartao):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Número de cartão inválido",
        )"""
    if not _validade_no_futuro(dados.validade):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cartão vencido ou validade inválida (use o formato MM/AA)",
        )

    resultado = tokenizador.tokenizar(dados.numero_cartao)

    cartao = CartaoORM(
        token=resultado["token"],
        ultimos_digitos=resultado["ultimos_digitos"],
        bandeira=resultado["bandeira"],
        nome_titular=dados.nome_titular,
        validade=dados.validade,
        apelido=dados.apelido,
    )
    return repo.add_cartao(email_usuario, cartao)


def listar_cartoes(email_usuario: str) -> list[CartaoORM]:
    return repo.list_cartoes(email_usuario)
