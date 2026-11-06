"""
dominio/avaria/reporte_avaria.py
----------------------------------------
Classe `ReporteAvaria` do diagrama: avaria reportada por um ciclista.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from servicos_tecnicos.banco_de_dados.enums import StatusAvaria

if TYPE_CHECKING:
    from dominio.bicicleta.bicicleta import Bicicleta
    from dominio.usuario.usuario import Usuario


class ReporteAvaria:
    """Construtor do diagrama: ReporteAvaria(bicicleta, usuario, descricao).

    Guarda a bicicleta com defeito e o usuário que reportou; bicicleta_id e
    usuario_email continuam como propriedades de leitura. O id
    (`id_reporte`) é dado pelo repositório.
    """

    def __init__(
        self,
        bicicleta: "Bicicleta",
        usuario: "Usuario",
        descricao: str,
        *,
        id_reporte: Optional[int] = None,
    ):
        self.id_reporte = id_reporte
        self.bicicleta = bicicleta
        self.usuario = usuario
        self.descricao = descricao
        self.data_hora = datetime.now()
        self.status = StatusAvaria.PENDENTE

    def __repr__(self) -> str:
        return (
            f"ReporteAvaria(id_reporte={self.id_reporte!r}, bicicleta_id={self.bicicleta_id!r}, "
            f"usuario_email={self.usuario_email!r}, status={self.status!r})"
        )

    # --- nomes antigos, só leitura ----------------------------------------
    @property
    def id(self) -> Optional[int]:
        return self.id_reporte

    @property
    def bicicleta_id(self) -> int:
        return self.bicicleta.id_bicicleta

    @property
    def usuario_email(self) -> str:
        return self.usuario.email

    def resolver(self) -> None:
        self.status = StatusAvaria.RESOLVIDO
