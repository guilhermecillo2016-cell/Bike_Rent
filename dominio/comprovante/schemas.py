from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from servicos_tecnicos.banco_de_dados.enums import StatusPagamento


class ComprovantePublic(BaseModel):
    id: int
    locacao_id: int
    data_emissao: datetime
    trajeto: str                    # "Origem → Destino"
    data_hora_inicio: datetime
    data_hora_fim: Optional[datetime]
    duracao_minutos: int
    minutos_pacote: int
    tarifa_aplicada: float          # só o excedente cobrado
    metodo_pagamento: str           # nunca o número completo do cartão
    pago_com_pacote: bool           # pacote cobriu a corrida inteira
    pagamento_status: Optional[StatusPagamento] = None