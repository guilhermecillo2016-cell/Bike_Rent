import os
from threading import TIMEOUT_MAX
import time
from enum import StrEnum
from typing import Optional

from servicos_tecnicos.iot.interface import TravaInteligente, ErroTrava

class ModoTrava(StrEnum):
    SUCESSO = "sucesso"
    TIMEOUT = "timeout"
    FALHA = "falha"


class TravaInteligenteMock(TravaInteligente):

    def __init__(self, modo: Optional[ModoTrava] = None, atraso_segundos : float = 0.0):
        """atraso_segundos : espera simulada antes de responder (0 nos testes para o timeout
        ser forcado sem demorar)"""
        self.modo = ModoTrava(modo or os.getenv("IOT_MODO", ModoTrava.SUCESSO))
        self.atraso_segundos = atraso_segundos
        self.aberturas : list[int] = []
        self.travas : list[tuple[int,int]] = []

    def _responder(self) -> bool:
        if self.atraso_segundos:
            time.sleep(self.atraso_segundos)
        if self.modo == ModoTrava.FALHA:
            raise ErroTrava("Falha de cominucação com a trava!")
        return self.modo == ModoTrava.SUCESSO

    def abrir(self, bicicleta_id):
        resultado = self._responder()

        if resultado:
            self.aberturas.append(bicicleta_id)
        return resultado

    def confirmar_travamento(self, bicicleta_id, estacao_id):
        resultado = self._responder()

        if resultado:
            self.travas.append((bicicleta_id, estacao_id))
        return resultado

    