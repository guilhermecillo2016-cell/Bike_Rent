"""
dominio/pagamento/metodos_pagamento.py
----------------------------------------
Padrão Strategy para a forma de pagamento (RF-12, RN-07). Cada estratégia sabe
processar um Pagamento do seu TipoPagamento e devolve o StatusPagamento
resultante; o PagamentoService escolhe a estratégia por um dicionário
TipoPagamento -> MetodoPagamento, sem if por tipo.

    MetodoPagamento (interface)
      |-- PagamentoCartaoCredito   cobra no gateway; resposta na hora
      |-- PagamentoCartaoDebito    cobra no gateway; resposta na hora
      `-- PagamentoPix             gera o código "copia e cola"; fica PENDENTE

A estratégia NÃO altera o status do pagamento: devolve o resultado e quem
chama aplica a transição. O gateway entra por injeção (qualquer objeto com
`cobrar(token, valor)`), então este módulo não conhece repositórios nem a
implementação do gateway.
"""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Callable, ClassVar, Optional, Protocol

from servicos_tecnicos.banco_de_dados.enums import StatusPagamento, TipoPagamento

if TYPE_CHECKING:
    from dominio.pagamento.pagamento import Pagamento
    from dominio.usuario.usuario import Usuario


class GatewayCobranca(Protocol):
    """O que as estratégias de cartão exigem de um gateway de pagamento."""

    def cobrar(self, token: str, valor: float) -> StatusPagamento: ...


class MetodoPagamento(ABC):
    """Interface da estratégia. `tipo` diz a qual TipoPagamento ela atende."""

    tipo: ClassVar[TipoPagamento]

    @abstractmethod
    def processar(
        self, pagamento: "Pagamento", usuario: Optional["Usuario"]
    ) -> StatusPagamento:
        """Processa o pagamento e devolve o status resultante: APROVADO ou
        RECUSADO quando a resposta é imediata (cartão), PENDENTE quando depende
        de confirmação posterior (PIX). `usuario` é o dono do pagamento; pode
        ser None só se o service for chamado direto com um e-mail sem cadastro."""

    def _conferir_tipo(self, pagamento: "Pagamento") -> None:
        if pagamento.tipo != self.tipo:
            raise ValueError(
                f"{type(self).__name__} atende {self.tipo}, não {pagamento.tipo}"
            )


class _PagamentoCartao(MetodoPagamento):
    """Parte comum do crédito e do débito: cobra no gateway o token do cartão
    que o service já colocou em `pagamento.token_cartao`."""

    def __init__(self, gateway: GatewayCobranca):
        self.gateway = gateway

    def processar(
        self, pagamento: "Pagamento", usuario: Optional["Usuario"]
    ) -> StatusPagamento:
        self._conferir_tipo(pagamento)
        return self.gateway.cobrar(pagamento.token_cartao, pagamento.valor)


class PagamentoCartaoCredito(_PagamentoCartao):
    tipo = TipoPagamento.CARTAO_CREDITO


class PagamentoCartaoDebito(_PagamentoCartao):
    tipo = TipoPagamento.CARTAO_DEBITO


class PagamentoPix(MetodoPagamento):
    """PIX simulado: gera o código "copia e cola", define a validade
    (`pagamento.expira_em`) e deixa o pagamento PENDENTE. A confirmação e o
    cancelamento por vencimento (`verificar_status_pix`) são tratados à parte
    (issue [C13])."""

    tipo = TipoPagamento.PIX

    def __init__(
        self,
        validade_minutos: int = 15,
        relogio: Callable[[], datetime] = datetime.now,
    ):
        self.validade_minutos = validade_minutos
        self.relogio = relogio

    def gerar_codigo(self, valor: float, validade: datetime) -> str:
        """Código simulado: identificador único, valor e validade."""
        return (
            f"BIKERENT-PIX|{uuid.uuid4().hex[:16].upper()}"
            f"|{valor:.2f}|{validade:%Y%m%d%H%M%S}"
        )

    def processar(
        self, pagamento: "Pagamento", usuario: Optional["Usuario"]
    ) -> StatusPagamento:
        self._conferir_tipo(pagamento)
        validade = self.relogio() + timedelta(minutes=self.validade_minutos)
        pagamento.qr_code_pix = self.gerar_codigo(pagamento.valor, validade)
        pagamento.expira_em = validade
        return StatusPagamento.PENDENTE
