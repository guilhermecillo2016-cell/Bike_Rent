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
from servicos_tecnicos.banco_de_dados.models import PagamentoORM
from dominio.pagamento.schemas import CartaoCreate
from servicos_tecnicos.pagamentos import gateway as gateway_simulado

class PagamentoService:
    """Regras de pagamento (RF-12, RN-06, RN-07).
 
    Os repositories e o gateway são módulos/objetos injetáveis; por padrão usa
    os repositories em memória e o gateway simulado.
    """
 
    def __init__(
        self, pagamento_repo=None, cartao_repo=None, locacao_repo=None, gateway=None
    ):
        self.pagamento_repo = pagamento_repo or repository_pagamento
        self.cartao_repo = cartao_repo or repository_cartao
        self.locacao_repo = locacao_repo  # opcional: sem ele, não checa a locação
        self.gateway = gateway or gateway_simulado
 
    # --- Consultas ----------------------------------------------------
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
 
    # --- Cobrança (RF-12, RN-06, RN-07) -------------------------------
    def cobrar_corrida(self, email, valor, locacao_id):
        """Cobra a corrida no cartão de crédito vinculado ao usuário.
 
        Recusa NÃO lança exceção: devolve o PagamentoORM com status RECUSADO
        para a locação decidir o que fazer.
        """
        self._validar_locacao(locacao_id)
        return self._cobrar(email, valor, locacao_id=locacao_id)
 
    def cobrar_pacote(self, email, valor, pacote_id):
        """Cobra a compra de um pacote de minutos (mesmo gateway da corrida)."""
        self._validar_pacote(pacote_id)
        return self._cobrar(email, valor, pacote_id=pacote_id)
 
    def exigir_cartao_credito(self, email):
        """RN-06: o usuário precisa ter cartão de crédito cadastrado.
 
        Chamar ao iniciar uma locação. Devolve o cartão ou levanta 400.
        """
        cartao = self.cartao_repo.get_credito_by_email(email)
        if cartao is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Usuário não possui cartão de crédito cadastrado",
            )
        return cartao
 
    def _cobrar(self, email, valor, locacao_id=None, pacote_id=None):
        self._validar_destino(locacao_id, pacote_id)
        self._validar_valor(valor)
        cartao = self.exigir_cartao_credito(email)
        # O pagamento nasce PENDENTE; o status final vem do gateway.
        pagamento = self.pagamento_repo.create(
            valor=valor,
            tipo=TipoPagamento.CARTAO_CREDITO,
            locacao_id=locacao_id,
            pacote_id=pacote_id,
            token_cartao=cartao.token,
        )
        pagamento.status = self.gateway.cobrar(cartao.token, valor)
        return pagamento
 
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
