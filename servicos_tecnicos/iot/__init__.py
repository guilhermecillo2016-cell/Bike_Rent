"""
servicos_tecnicos/iot
------------------------
Serviço técnico "IoT": comunicação com travas/sensores das bicicletas.
O domínio usa obter_trava() e a interface TravaInteligente; trocar o
mock por hardware real (ou por outro mock nos testes) é só chamar
definir_trava().
"""

from tkinter import NO
from token import OP
from typing import Optional

from pydantic.types import T

from servicos_tecnicos.iot.interface import ErroTrava, TravaInteligente

__all__ = ["ErroTrava", "TravaInteligente", "obter_trava", "definir_trava"]

_trava: Optional[TravaInteligente] = None


def obter_trava() -> TravaInteligente:
    global _trava

    if _trava is None:

        from servicos_tecnicos.iot.mock import TravaInteligenteMock

        _trava = TravaInteligenteMock()

    return _trava

def definir_trava(trava: Optional[TravaInteligente]) -> None:
    global _trava
    _trava = trava
