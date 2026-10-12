"""
dominio/bicicleta/schemas.py
------------------------------
Schemas do domínio Bicicleta — cadastro pelo administrador e listagem
para a equipe (administrador e operador de campo).
"""

from pydantic import BaseModel, Field

from servicos_tecnicos.banco_de_dados.enums import StatusBicicleta


class BicicletaCreate(BaseModel):
    """Só a estação inicial: o id e o qr_code são gerados pelo sistema."""

    estacao_id: int = Field(gt=0)


class StatusBicicletaUpdate(BaseModel):
    status: StatusBicicleta


class BicicletaPublic(BaseModel):
    id: int
    qr_code: str
    status: StatusBicicleta
    estacao_id: int | None = None  # None enquanto estiver EM_USO
    bloqueio_pendente: bool

class QrValidarRequest(BaseModel):
    qr_code : str = Field(min_length=1)