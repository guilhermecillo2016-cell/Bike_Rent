# exceptions.py
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

def registrar_exception_handlers(app):
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        erros_personalizados = [
            {"campo": error.get("loc", [])[-1], "mensagem": error.get("msg")}
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Há campos obrigatórios vazios ou preenchidos incorretamente.",
                "erros": erros_personalizados
            }
        )