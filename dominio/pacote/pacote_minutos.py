"""
dominio/pacote/pacote_minutos.py
----------------------------------------
Classe `PacoteMinutos` do diagrama: pacote de minutos comprado pelo usuário.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from dominio.usuario.usuario import Usuario


class PacoteMinutos:
    """Construtor do diagrama: PacoteMinutos(minutos, validade). O dono
    (`usuario`) e o id (`id_pacote`, dado pelo repositório) entram como
    parâmetros opcionais."""

    def __init__(
        self,
        minutos: int,
        validade: datetime,
        *,
        usuario: Optional["Usuario"] = None,
        id_pacote: Optional[int] = None,
    ):
        self.id_pacote = id_pacote
        self.usuario = usuario
        self.minutos_totais = minutos
        self.minutos_restantes = minutos
        self.data_validade = validade
        # False até o pagamento da compra ser aprovado
        self.ativo = False

    def __repr__(self) -> str:
        return (
            f"PacoteMinutos(id_pacote={self.id_pacote!r}, usuario_email={self.usuario_email!r}, "
            f"minutos_restantes={self.minutos_restantes!r}/{self.minutos_totais!r}, ativo={self.ativo!r})"
        )

    @property
    def id(self) -> Optional[int]:
        return self.id_pacote

    @property
    def usuario_email(self) -> Optional[str]:
        return self.usuario.email if self.usuario is not None else None

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
