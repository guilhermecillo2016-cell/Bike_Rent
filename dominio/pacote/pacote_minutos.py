"""
dominio/pacote/pacote_minutos.py
----------------------------------------
Classe `PacoteMinutos` do diagrama: pacote de minutos comprado pelo usuário.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class PacoteMinutos:
    id: int
    usuario_email: str
    minutos_totais: int
    minutos_restantes: int
    data_validade: datetime
    # False até o pagamento da compra ser aprovado
    ativo: bool = False

    def ativar(self) -> None:
        """Compra aprovada: o pacote passa a valer com todos os minutos (RF-10)."""
        self.minutos_restantes = self.minutos_totais
        self.ativo = True

    def atualizar_situacao(self, agora: datetime) -> None:
        """Pacote ativo que venceu ou zerou passa a ativo=False."""
        if self.ativo and (self.minutos_restantes <= 0 or self.data_validade <= agora):
            self.ativo = False

    def consumir(self, minutos: int, agora: datetime) -> int:
        """Tira até `minutos` do saldo e devolve quantos tirou. Se zerar, o
        pacote deixa de ficar ativo."""
        consumo = min(self.minutos_restantes, minutos)
        self.minutos_restantes -= consumo
        self.atualizar_situacao(agora)
        return consumo
