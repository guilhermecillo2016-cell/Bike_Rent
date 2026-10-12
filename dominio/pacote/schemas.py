from datetime import datetime

from pydantic import BaseModel, ConfigDict

from servicos_tecnicos.banco_de_dados.enums import StatusPagamento


class ItemCatalogo(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    minutos: int
    preco: float
    validade_dias: int


class CompraPacoteRequest(BaseModel):
    item_id: int


class PacoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    minutos_totais: int
    minutos_restantes: int
    data_validade: datetime
    ativo: bool


class PacoteCompradoResponse(BaseModel):
    pacote: PacoteResponse
    pagamento_status: StatusPagamento