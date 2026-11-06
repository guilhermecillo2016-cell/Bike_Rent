"""
dominio/avaria/reporte_avaria.py
----------------------------------------
Classe `ReporteAvaria` do diagrama: avaria reportada por um ciclista.
"""

from dataclasses import dataclass
from datetime import datetime

from servicos_tecnicos.banco_de_dados.enums import StatusAvaria


@dataclass
class ReporteAvaria:
    id: int
    descricao: str
    data_hora: datetime
    usuario_email: str
    bicicleta_id: int
    status: StatusAvaria = StatusAvaria.PENDENTE

    def resolver(self) -> None:
        self.status = StatusAvaria.RESOLVIDO
