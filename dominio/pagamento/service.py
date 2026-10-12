"""
dominio/pagamento/service.py
------------------------------
Regras de negócio do domínio Pagamento: validação dos dados do
cartão (Luhn, validade) e vínculo com o usuário autenticado, delegando
a tokenização ao serviço técnico correspondente.
"""

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from fastapi import HTTPException, status

from servicos_tecnicos.pagamentos import tokenizador
from servicos_tecnicos.banco_de_dados import repository_cartao as repo
from servicos_tecnicos.banco_de_dados.enums import TipoPagamento
from servicos_tecnicos.banco_de_dados.models import CartaoORM
from dominio.pagamento.schemas import CartaoCreate

class PagamentoService:
    TIPOS_SUPORTADOS = {TipoPagamento.CARTAO_CREDITO, TipoPagamento.CARTAO_DEBITO}
    TIPOS_ADIADOS = {TipoPagamento.PIX}  # iteração 3
 
    def __init__(self, pagamento_repo, cartao_repo, locacao_repo=None):
        self.pagamento_repo = pagamento_repo
        self.cartao_repo = cartao_repo
        self.locacao_repo = locacao_repo
 
    # --- Operações públicas -------------------------------------------
    def criar_pagamento(self, dados, usuario_id):
        """`usuario_id` vem do usuário autenticado, nunca do corpo da requisição."""
        self._validar_destino(dados.locacao_id, dados.pacote_id)
        self._validar_valor(dados.valor)
        self._validar_tipo(dados.tipo)
        self._validar_cartao(dados.cartao_id, usuario_id)
        self._validar_locacao(dados.locacao_id)
        self._validar_pacote(dados.pacote_id)
        return self.pagamento_repo.create(dados)
 
    def obter_pagamento(self, pagamento_id):
        pagamento = self.pagamento_repo.get_by_id(pagamento_id)
        if pagamento is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pagamento não encontrado",
            )
        return pagamento
 
    def listar_pagamentos(self):
        return self.pagamento_repo.list_all()
 
    # --- Validações ---------------------------------------------------
    @staticmethod
    def _validar_destino(locacao_id, pacote_id):
        """XOR: exatamente um entre locacao_id e pacote_id."""
        if (locacao_id is None) == (pacote_id is None):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Informe exatamente um entre locacao_id e pacote_id",
            )
 
    @staticmethod
    def _validar_valor(valor):
        try:
            valor_decimal = Decimal(str(valor))
        except (InvalidOperation, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Valor inválido",
            )
        if not valor_decimal.is_finite() or valor_decimal <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O valor deve ser maior que zero",
            )
 
    @classmethod
    def _validar_tipo(cls, tipo):
        try:
            tipo = TipoPagamento(tipo)  # aceita o membro do enum ou seu valor
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tipo de pagamento inválido",
            )
        if tipo in cls.TIPOS_ADIADOS:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"Pagamento via {tipo.name} ainda não está disponível",
            )
        if tipo not in cls.TIPOS_SUPORTADOS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tipo de pagamento não suportado",
            )
 
    def _validar_cartao(self, cartao_id, usuario_id):
        if cartao_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="cartao_id é obrigatório para pagamento com cartão",
            )
        cartao = self.cartao_repo.get_by_id(cartao_id)
        if cartao is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cartão não encontrado",
            )
        if cartao.usuario_id != usuario_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="O cartão não pertence ao usuário",
            )
 
    def _validar_locacao(self, locacao_id):
        if locacao_id is None or self.locacao_repo is None:
            return
        if self.locacao_repo.get_by_id(locacao_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Locação não encontrada",
            )
 
    def _validar_pacote(self, pacote_id):
        # TODO [C8]: checar existência do pacote (404 "Pacote não encontrado")
        # quando o repository de pacote de minutos existir (iteração 2).
        # Por ora, só vale o XOR.
        return

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
        tipo=dados.tipo,
        apelido=dados.apelido
        
    )
    return repo.add_cartao(email_usuario, cartao)


def listar_cartoes(email_usuario: str) -> list[CartaoORM]:
    return repo.list_cartoes(email_usuario)
#Retorna falso se não encontrou o cartão ou se não pertence ao usuário, caso contrário remove e retorna verdadeiro
def remover_cartao(email_usuario: str, token: str) -> bool:
    cartao = repo.get_cartao(email_usuario, token)
    if not cartao:
        return False
    repo.remover_cartao(email_usuario, cartao)
    return True
