"""
dominio/comprovante/comprovante_viagem.py
-------------------------------------------------
Classe `ComprovanteViagem` do diagrama: comprovante digital da corrida.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ComprovanteViagem:
    id: int
    data_emissao: datetime
    resumo_trajeto: str
    tarifa_aplicada: float
    locacao_id: int
    # None quando o pacote cobriu a corrida inteira (não houve cobrança)
    pagamento_id: Optional[int] = None
