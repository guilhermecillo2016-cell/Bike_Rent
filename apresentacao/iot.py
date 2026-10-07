from fastapi import APIRouter
from pydantic import BaseModel

from servicos_tecnicos.iot import get_trava

router = APIRouter(prefix="/iot", tags=["IOT (simulação)"])

class TravamentoIn(BaseModel):
    bicicleta_id : int
    estacao_id : int

@router.post("/travamento")
def simular_travamento(dados: TravamentoIn):
    ok = get_trava().confirmar_travamento(dados.bicicleta_id, dados.estacao_id)
    return {"confirmado" : ok}

