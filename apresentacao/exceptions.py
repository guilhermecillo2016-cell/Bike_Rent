from fastapi.responses import JSONResponse
from fastapi import status
from dominio.bicicleta import service as bicicleta_service

def _resposta_indisponivel(e: bicicleta_service.BicicletaIndisponivel) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "detail": "Bicicleta indisponível por razões operacionais",
            "sugestoes": [
                bicicleta_service.to_public(b).model_dump(mode="json")
                for b in e.sugestoes
            ],
        },
    )