"""
dominio/relatorio/schemas.py
------------------------------
Formato do relatório analítico do administrador (UC3, RF-17). Os campos
principais são os do RelatorioAnalitico do diagrama de projeto; nada
disso é guardado, o relatório é calculado a cada pedido.
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class HorarioPico(BaseModel):
    estacao_id: int
    estacao_nome: str
    total_locacoes: int
    hora_pico: int  # 0 a 23
    locacoes_na_hora_pico: int


class RelatorioAnalitico(BaseModel):
    data_geracao: datetime

    # filtros aplicados (None = sem filtro)
    inicio: Optional[date] = None
    fim: Optional[date] = None
    estacao_id: Optional[int] = None

    receita_total: float
    receita_corridas: float
    receita_pacotes: float

    total_locacoes: int

    bicicletas_total: int
    bicicletas_ociosas: int
    taxa_ociosidade: float  # 0 a 1

    total_avarias: int
    indice_quebras: float  # avarias por locação

    horarios_pico: list[HorarioPico]
