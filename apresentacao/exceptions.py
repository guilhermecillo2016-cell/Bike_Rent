from fastapi.responses import JSONResponse
from fastapi import status
from dominio.bicicleta import service as bicicleta_service
from dominio.estacao import service as estacao_service
from dominio.locacao import service as locacao_service


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

def _resposta_estacao_indisponivel(e: locacao_service.EstacaoDestinoIndisponivel) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "detail": e.motivo,
            "sugestoes": [
                estacao_service.to_public(est).model_dump(mode="json")
                for est in e.sugestoes
            ],
        },
    )