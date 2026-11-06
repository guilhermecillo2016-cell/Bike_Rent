"""
dominio/erros.py
------------------
Erros de regra de negócio levantados pelas próprias entidades.

Herdam de HTTPException de propósito: o FastAPI já sabe responder e os
testes que esperam HTTPException continuam valendo, com o mesmo código
HTTP e a mesma mensagem de antes.
"""

from fastapi import HTTPException, status


class ErroDeDominio(HTTPException):
    """Violação de uma regra do domínio."""


class RecursoNaoEncontrado(ErroDeDominio):
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class ConflitoDeRegra(ErroDeDominio):
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class RequisicaoInvalida(ErroDeDominio):
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
