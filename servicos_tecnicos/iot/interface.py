from abc import ABC, abstractmethod

class ErroTrava(Exception):
    """FALHA DE COMUNICACAO/HARDWARE COM A TRAVA"""

class TravaInteligente(ABC):

    @abstractmethod
    def abrir(self, bicicleta_id: int) -> bool:
        """
        Manda trava abrir e espera confirmação mecanica

        retorna True se a trava abriu sem problema e pode-se iniciar a contagem do tempo
        retorna False se a trava não conseguir abrir sem a confirmação mecanica
        """
    @abstractmethod
    def confirmar_travamento(self, bicicleta_id: int, estacao_id: int) -> bool:
        """Confirma que a bicicleta foi travada fisicamente na estação.

        True  -> travamento detectado
        False -> não detectado (timeout)
        Levanta ErroTrava em falha de comunicação/hardware.
        """