"""
apresentacao/iot.py
---------------------
Rota de simulação para o front/demo "travar" a bicicleta fisicamente
(RF-09). Em produção quem avisa é o hardware, não o navegador.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from servicos_tecnicos.iot import ErroTrava, obter_trava

router = APIRouter(prefix="/iot", tags=["IoT (simulação)"])


class TravamentoSimulado(BaseModel):
    bicicleta_id: int = Field(gt=0)
    estacao_id: int = Field(gt=0)


class TravamentoResposta(BaseModel):
    confirmado: bool


@router.post("/travamento", response_model=TravamentoResposta)
def simular_travamento(dados: TravamentoSimulado):
    try:
        confirmado = obter_trava().confirmar_travamento(
            dados.bicicleta_id, dados.estacao_id
        )
    except ErroTrava as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    if not confirmado:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Travamento não confirmado (timeout)",
        )
    return TravamentoResposta(confirmado=True)