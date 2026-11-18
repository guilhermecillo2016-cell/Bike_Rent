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
from servicos_tecnicos.banco_de_dados import (
    repository_locacao,
    repository_pacote,
    repository_pagamento,
    repository_usuario,
)
from servicos_tecnicos.banco_de_dados.enums import StatusPagamento, TipoPagamento
from dominio.pagamento.cartao import Cartao
from dominio.pagamento.metodos_pagamento import (
    PagamentoCartaoCredito,
    PagamentoCartaoDebito,
    PagamentoPix,
)
from dominio.pagamento.pagamento import Pagamento
from dominio.pagamento.schemas import CartaoCreate
from servicos_tecnicos.pagamentos.gateway import GatewayPagamento

_TIPOS_CARTAO = {
    "credito" : TipoPagamento.CARTAO_CREDITO,
    "crédito" : TipoPagamento.CARTAO_CREDITO,
    "debito" : TipoPagamento.CARTAO_DEBITO,
    "débito" : TipoPagamento.CARTAO_DEBITO
}

def _normalizar_tipo(tipo: str):
    chave = (tipo or "").strip().lower()
    if chave in {t.value.lower() for t in TipoPagamento}:
        chave = chave.replace("cartao_", "")
    resultado = _TIPOS_CARTAO.get(chave)
    if resultado is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de cartão inválido (use crédito ou débito)",
        )
    return resultado.value

class PagamentoService:
    """Regras de pagamento (RF-12, RN-06, RN-07).
 
    Os repositories e o gateway são módulos/objetos injetáveis; por padrão usa
    os repositories em memória e o gateway simulado.

    A forma de pagamento é uma estratégia (padrão Strategy): `metodos` mapeia
    cada TipoPagamento para o MetodoPagamento que o processa.
    """
 
    def __init__(
        self, pagamento_repo=None, cartao_repo=None, locacao_repo=None,
        pacote_repo=None, gateway=None, usuario_repo=None,
    ):
        self.pagamento_repo = pagamento_repo or repository_pagamento
        self.cartao_repo = cartao_repo or repo
        self.locacao_repo = locacao_repo or repository_locacao
        self.pacote_repo = pacote_repo or repository_pacote
        self.gateway = gateway or GatewayPagamento()
        self.usuario_repo = usuario_repo or repository_usuario
        self.metodos = {
            metodo.tipo: metodo
            for metodo in (
                PagamentoCartaoCredito(self.gateway),
                PagamentoCartaoDebito(self.gateway),
                PagamentoPix(),
            )
        }
        # Qual cartão cada tipo exige (o PIX não usa cartão).
        self._cartao_do_tipo = {
            TipoPagamento.CARTAO_CREDITO: self.exigir_cartao_credito,
            TipoPagamento.CARTAO_DEBITO: self.exigir_cartao_debito,
        }
 
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
 
        Recusa NÃO lança exceção: devolve o Pagamento com status RECUSADO
        para a locação decidir o que fazer.
        """
        locacao = self._obter_locacao(locacao_id)
        return self._cobrar(email, valor, locacao=locacao)
 
    def cobrar_pacote(self, email, valor, pacote_id, tipo=TipoPagamento.CARTAO_CREDITO):
        """Cobra a compra de um pacote de minutos (mesmo gateway da corrida).
        `tipo` escolhe a estratégia; o padrão é o cartão de crédito."""
        pacote = self._obter_pacote(pacote_id)
        return self._cobrar(email, valor, pacote=pacote, tipo=tipo)
 
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
 
    def exigir_cartao_debito(self, email):
        """Para pagar no débito o usuário precisa ter cartão de débito cadastrado."""
        cartao = self.cartao_repo.get_debito_by_email(email)
        if cartao is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Usuário não possui cartão de débito cadastrado",
            )
        return cartao

    def _metodo_de(self, tipo):
        metodo = self.metodos.get(tipo)
        if metodo is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Forma de pagamento não suportada",
            )
        return metodo

    def _cobrar(self, email, valor, locacao=None, pacote=None,
                tipo=TipoPagamento.CARTAO_CREDITO):
        self._validar_destino(locacao, pacote)
        self._validar_valor(valor)
        metodo = self._metodo_de(tipo)
        # Cartão do tipo certo (400 se faltar); o PIX não usa cartão.
        buscar_cartao = self._cartao_do_tipo.get(tipo)
        token = buscar_cartao(email).token if buscar_cartao else None
        # O pagamento nasce PENDENTE; o status final vem da estratégia.
        pagamento = self.pagamento_repo.create(
            valor=valor,
            tipo=tipo,
            locacao=locacao,
            pacote=pacote,
            token_cartao=token,
        )
        usuario = self.usuario_repo.get_by_email(email)
        resultado = metodo.processar(pagamento, usuario)
        self._aplicar_resultado(pagamento, resultado)
        return pagamento

    @staticmethod
    def _aplicar_resultado(pagamento, resultado):
        """Aplica o resultado da estratégia pelas transições do próprio
        Pagamento (nunca atribui `status` direto). PENDENTE: nada a fazer."""
        transicoes = {
            StatusPagamento.APROVADO: pagamento.aprovar,
            StatusPagamento.RECUSADO: pagamento.recusar,
            StatusPagamento.CANCELADO: pagamento.cancelar,
        }
        transicao = transicoes.get(resultado)
        if transicao is not None:
            transicao()
 
    # --- Cartões (RF-11, RN-06) ---------------------------------------
    def vincular_cartao(self, email_usuario: str, dados: CartaoCreate) -> Cartao:
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

        cartao = Cartao(
            token=resultado["token"],
            ultimos_digitos=resultado["ultimos_digitos"],
            bandeira=resultado["bandeira"],
            nome_titular=dados.nome_titular,
            validade=dados.validade,
            tipo=_normalizar_tipo(dados.tipo),
            apelido=dados.apelido
        )
        return self.cartao_repo.add_cartao(email_usuario, cartao)

    def listar_cartoes(self, email_usuario: str) -> list[Cartao]:
        return self.cartao_repo.list_cartoes(email_usuario)

    def remover_cartao(self, email_usuario: str, token: str) -> bool:
        """Falso se não achou o cartão ou se ele não é do usuário; senão
        remove e devolve verdadeiro."""
        cartao = self.cartao_repo.get_cartao(email_usuario, token)
        if not cartao:
            return False
        self.cartao_repo.remover_cartao(email_usuario, cartao)
        return True

    # --- Validações ---------------------------------------------------
    @staticmethod
    def _validar_destino(locacao, pacote):
        """XOR: exatamente um entre locação e pacote (ids ou objetos)."""
        if (locacao is None) == (pacote is None):
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
 
    def _obter_locacao(self, locacao_id):
        """A locação paga (404 se não existe). None se não veio id."""
        if locacao_id is None:
            return None
        locacao = self.locacao_repo.get_by_id(locacao_id)
        if locacao is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Locação não encontrada",
            )
        return locacao

    def _obter_pacote(self, pacote_id):
        """O pacote pago (404 se não existe). None se não veio id."""
        if pacote_id is None:
            return None
        pacote = self.pacote_repo.get_by_id(pacote_id)
        if pacote is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pacote não encontrado",
            )
        return pacote


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




# ----------------------------------------------------------------------
# Fachada de módulo (mesmas assinaturas de sempre): quem faz o trabalho é
# a classe PagamentoService.
# ----------------------------------------------------------------------
def vincular_cartao(email_usuario: str, dados: CartaoCreate) -> Cartao:
    return PagamentoService().vincular_cartao(email_usuario, dados)


def listar_cartoes(email_usuario: str) -> list[Cartao]:
    return PagamentoService().listar_cartoes(email_usuario)


# Retorna falso se não encontrou o cartão ou se não pertence ao usuário,
# caso contrário remove e retorna verdadeiro
def remover_cartao(email_usuario: str, token: str) -> bool:
    return PagamentoService().remover_cartao(email_usuario, token)
