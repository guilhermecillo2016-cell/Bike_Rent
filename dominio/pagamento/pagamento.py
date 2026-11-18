"""
dominio/pagamento/pagamento.py
--------------------------------------
Classe `Pagamento` do diagrama: paga uma corrida OU a compra de um pacote.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from dominio.erros import ConflitoDeRegra
from servicos_tecnicos.banco_de_dados.enums import StatusPagamento, TipoPagamento

if TYPE_CHECKING:
    from dominio.locacao.locacao import Locacao
    from dominio.pacote.pacote_minutos import PacoteMinutos


class Pagamento:
    """Paga uma corrida OU a compra de um pacote: exatamente um entre
    `locacao` e `pacote` deve estar preenchido (validado no service).

    Construtor do diagrama: Pagamento(valor, tipo). A locação/pacote pagos,
    o token do cartão e o id (`id_pagamento`, dado pelo repositório) entram
    como parâmetros opcionais. Nasce PENDENTE e muda de estado uma única vez:

        PENDENTE --aprovar()--> APROVADO
        PENDENTE --recusar()--> RECUSADO
        PENDENTE --cancelar()--> CANCELADO   (PIX que venceu: verificar_status_pix)

    APROVADO, RECUSADO e CANCELADO são finais: qualquer nova transição levanta
    ConflitoDeRegra (409). `expira_em` é a validade do código PIX (None nos demais).
    """

    def __init__(
        self,
        valor: float,
        tipo: TipoPagamento,
        *,
        locacao: Optional["Locacao"] = None,
        pacote: Optional["PacoteMinutos"] = None,
        token_cartao: Optional[str] = None,
        qr_code_pix: Optional[str] = None,
        expira_em: Optional[datetime] = None,
        id_pagamento: Optional[int] = None,
    ):
        self.id_pagamento = id_pagamento
        self.valor = valor
        self.tipo = tipo
        self.data_hora = datetime.now()
        self.status = StatusPagamento.PENDENTE
        self.locacao = locacao
        self.pacote = pacote
        self.token_cartao = token_cartao
        self.qr_code_pix = qr_code_pix
        self.expira_em = expira_em

    def __repr__(self) -> str:
        return (
            f"Pagamento(id_pagamento={self.id_pagamento!r}, valor={self.valor!r}, "
            f"tipo={self.tipo!r}, status={self.status!r}, "
            f"locacao_id={self.locacao_id!r}, pacote_id={self.pacote_id!r})"
        )

    # --- nomes antigos, só leitura ----------------------------------------
    @property
    def id(self) -> Optional[int]:
        return self.id_pagamento

    @property
    def locacao_id(self) -> Optional[int]:
        return self.locacao.id_locacao if self.locacao is not None else None

    @property
    def pacote_id(self) -> Optional[int]:
        return self.pacote.id_pacote if self.pacote is not None else None

    # --- transições de estado ---------------------------------------------
    def _sair_de_pendente(self, destino: StatusPagamento) -> None:
        if self.status != StatusPagamento.PENDENTE:
            raise ConflitoDeRegra(
                f"Pagamento {self.status} não pode passar para {destino}: "
                "só um pagamento PENDENTE muda de estado"
            )
        self.status = destino

    def aprovar(self) -> None:
        """PENDENTE -> APROVADO. Em qualquer outro estado levanta ConflitoDeRegra."""
        self._sair_de_pendente(StatusPagamento.APROVADO)

    def recusar(self) -> None:
        """PENDENTE -> RECUSADO. Em qualquer outro estado levanta ConflitoDeRegra."""
        self._sair_de_pendente(StatusPagamento.RECUSADO)

    def cancelar(self) -> None:
        """PENDENTE -> CANCELADO. Em qualquer outro estado levanta ConflitoDeRegra."""
        self._sair_de_pendente(StatusPagamento.CANCELADO)

    def verificar_status_pix(self, agora: datetime) -> StatusPagamento:
        """Cancela o pagamento PIX que venceu e devolve o status atual.

        Cancela só se o tipo é PIX, o status é PENDENTE e `expira_em <= agora`.
        Em qualquer outro caso (pagamento que não é PIX, que já saiu de PENDENTE
        ou sem `expira_em`) não muda nada e devolve o status atual, sem erro:
        pode ser chamado a cada consulta, quantas vezes for preciso.
        """
        if (
            self.tipo == TipoPagamento.PIX
            and self.status == StatusPagamento.PENDENTE
            and self.expira_em is not None
            and self.expira_em <= agora
        ):
            self.cancelar()
        return self.status
