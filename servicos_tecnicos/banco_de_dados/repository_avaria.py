"""
servicos_tecnicos/banco_de_dados/repository_avaria.py
-----------------------------------------------------------
Armazenamento em memória dos reportes de avaria feitos pelo ciclista
ao encerrar a corrida. A mudança de status da bicicleta para
EM_MANUTENCAO é feita pelo service, não aqui.
"""

from typing import Optional

from servicos_tecnicos.banco_de_dados import memoria
from dominio.avaria.reporte_avaria import ReporteAvaria
from dominio.bicicleta.bicicleta import Bicicleta
from dominio.usuario.usuario import Usuario


def create(
        bicicleta: Bicicleta,
        usuario: Usuario,
        descricao: str,
        ) -> ReporteAvaria:
    avaria = ReporteAvaria(
        bicicleta, usuario, descricao,
        id_reporte=memoria.proximo_id("avarias"),
    )
    memoria.avarias[avaria.id_reporte] = avaria
    return avaria


def get_by_id(avaria_id: int) -> Optional[ReporteAvaria]:
    return memoria.avarias.get(avaria_id)


def list_all() -> list[ReporteAvaria]:
    return list(memoria.avarias.values())


def list_by_bicicleta(bicicleta_id: int) -> list[ReporteAvaria]:
    return [a for a in memoria.avarias.values() if a.bicicleta_id == bicicleta_id]
