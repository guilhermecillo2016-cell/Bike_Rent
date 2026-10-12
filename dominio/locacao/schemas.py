"""
dominio/locacao/schemas.py
----------------------------
Schemas do domínio Locacao — início de corrida (B3).
"""
from token import OP
from typing import Optional

from datetime import datetime
from pydantic import BaseModel, Field

from servicos_tecnicos.banco_de_dados.enums import StatusPagamento


class LocacaoCreate(BaseModel):
    qr_code: str = Field(min_length=1)


class LocacaoPublic(BaseModel):
    id: int
    bicicleta_id: int
    estacao_origem_id: int
    data_hora_inicio: datetime
    em_andamento: bool

class LocacaoAndamento(BaseModel):
    locacao_id: int
    bicicleta_id: int
    estacao_origem_id: int
    estacao_origem_nome: str
    data_hora_inicio: datetime
    duracao_segundos: int
    duracao_minutos: int          # minutos iniciados (teto), base da tarifa
    minutos_pacote: int           # quanto do saldo do pacote cobriria a corrida
    custo_estimado: float         # só o excedente, já descontado o pacote

class EncerrarLocacaoRequest(BaseModel):
    estacao_id: int = Field(gt=0)
    descricao_avaria: Optional[str] = Field(default=True, max_length=500)

class LocacaoEncerrada(BaseModel):
    locacao_id: int
    bicicleta_id: int
    estacao_origem_id: int
    estacao_destino_id: int
    data_hora_inicio: datetime
    data_hora_fim: datetime
    duracao_segundos: int
    duracao_minutos: int
    minutos_pacote: int            # minutos abatidos do pacote
    valor_total: float             # só o excedente (RN-04/RN-05)
    pagamento_status: Optional[StatusPagamento] = None  # None = nada cobrado/cobrança não feita
    cobranca_pendente: bool        # True se havia valor a cobrar e não foi aprovado
    bicicleta_em_manutencao: bool  # bloqueio agendado foi aplicado
    avaria_reportada: bool = False