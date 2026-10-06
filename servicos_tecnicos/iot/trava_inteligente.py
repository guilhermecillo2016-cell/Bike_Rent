from abc import ABC, abstractmethod

class TravaInteligente:

    @abstractmethod
    def abrir(bicicleta_id : int) -> bool:
        """Envia o comando de liberação. True só com confirmação mecânica;
        False se falhou ou estourou o timeout."""

    @abstractmethod
    def confirmar_travamento(bicicleta_id : int, estacao_id : int) -> bool:
        """Registra que a bicicleta foi travada fisicamente na estação."""