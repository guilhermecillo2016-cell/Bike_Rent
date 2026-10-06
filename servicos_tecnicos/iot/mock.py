import os
import time
from enum import Enum
from trava_inteligente import TravaInteligente

class ModoTrava(str, Enum):
    SUCESSO = "sucesso"
    TIMEOUT = "timeout"
    FALHA = "falha"


class TravaMock(TravaInteligente):
    def __init__(self, modo : ModoTrava | None = None, timeout_s : float = 5.0):
        self.modo = modo or ModoTrava(os.get_env("IOT_MODO", "sucesso"))
        self.timeout_s = timeout_s

    def abrir(self, bicicleta_id : int) -> bool:
        if self.modo == ModoTrava.TIMEOUT:
            time.sleep(self.timeout_s)
            return False
        return self.modo == ModoTrava.SUCESSO

    def confirmar_travamento(self, bicicleta_id : int, estacao_id: int) -> bool:
        return self.modo == ModoTrava.SUCESSO