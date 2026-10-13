from typing import Optional

from pydantic import BaseModel

from servicos_tecnicos.banco_de_dados.enums import StatusEstacao


class EstacaoDisponibilidade(BaseModel):
    """Estação com o que o ciclista precisa para escolher onde retirar/devolver."""

    id: int
    nome: str
    endereco: str
    status: StatusEstacao
    bicicletas_disponiveis: int
    vagas_livres: int
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    distancia_metros: Optional[float] = None  # só quando há lat/lng