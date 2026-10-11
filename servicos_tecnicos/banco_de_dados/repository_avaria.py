"""
servicos_tecnicos/banco_de_dados/repository_avaria.py
-----------------------------------------------------------
Armazenamento em memória dos reportes de avaria feitos pelo ciclista
ao encerrar a corrida. A mudança de status da bicicleta para
EM_MANUTENCAO é feita pelo service, não aqui.
"""

from datetime import datetime
from typing import Optional

from servicos_tecnicos.banco_de_dados import memoria
from servicos_tecnicos.banco_de_dados.models import ReporteAvariaORM


def create(
        descricao: str,
        usuario_email: str,
        bicicleta_id: int,
        ) -> ReporteAvariaORM:
    avaria = ReporteAvariaORM(
        id=memoria.proximo_id("avarias"),
        descricao=descricao,
        data_hora=datetime.now(),
        usuario_email=usuario_email,
        bicicleta_id=bicicleta_id,
    )
    memoria.avarias[avaria.id] = avaria
    return avaria


def get_by_id(avaria_id: int) -> Optional[ReporteAvariaORM]:
    return memoria.avarias.get(avaria_id)


def list_all() -> list[ReporteAvariaORM]:
    return list(memoria.avarias.values())


def list_by_bicicleta(bicicleta_id: int) -> list[ReporteAvariaORM]:
    return [a for a in memoria.avarias.values() if a.bicicleta_id == bicicleta_id]
