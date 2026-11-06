"""
dominio/pagamento/pagamento.py
--------------------------------------
Classe `Pagamento` do diagrama: paga uma corrida OU a compra de um pacote.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from servicos_tecnicos.banco_de_dados.enums import StatusPagamento, TipoPagamento


@dataclass
class Pagamento:
    """Paga uma corrida OU a compra de um pacote: exatamente um entre
    locacao_id e pacote_id deve estar preenchido (validado no service)."""

    id: int
    valor: float
    tipo: TipoPagamento
    data_hora: datetime
    status: StatusPagamento = StatusPagamento.PENDENTE
    locacao_id: Optional[int] = None
    pacote_id: Optional[int] = None
    token_cartao: Optional[str] = None
    qr_code_pix: Optional[str] = None
