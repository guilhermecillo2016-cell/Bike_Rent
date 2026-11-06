"""
dominio/pagamento/pagamento.py
--------------------------------------
Classe `Pagamento` do diagrama: paga uma corrida OU a compra de um pacote.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from servicos_tecnicos.banco_de_dados.enums import StatusPagamento, TipoPagamento

if TYPE_CHECKING:
    from dominio.locacao.locacao import Locacao
    from dominio.pacote.pacote_minutos import PacoteMinutos


class Pagamento:
    """Paga uma corrida OU a compra de um pacote: exatamente um entre
    `locacao` e `pacote` deve estar preenchido (validado no service).

    Construtor do diagrama: Pagamento(valor, tipo). A locação/pacote pagos,
    o token do cartão e o id (`id_pagamento`, dado pelo repositório) entram
    como parâmetros opcionais. Nasce PENDENTE até o gateway responder.
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
