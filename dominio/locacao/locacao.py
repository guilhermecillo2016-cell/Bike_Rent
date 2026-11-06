"""
dominio/locacao/locacao.py
----------------------------------
Classe `Locacao` do diagrama: a corrida. A tarifa (RN-04) é regra dela.
"""

import os
from datetime import datetime
from typing import TYPE_CHECKING, ClassVar, Optional

if TYPE_CHECKING:
    from dominio.bicicleta.bicicleta import Bicicleta
    from dominio.estacao.estacao import Estacao
    from dominio.usuario.usuario import Usuario


class Locacao:
    """Construtor do diagrama: Locacao(usuario, bicicleta, origem).

    Guarda os objetos (usuario, bicicleta, estacao_origem e, depois de
    encerrar, estacao_destino). Os nomes antigos (usuario_email,
    bicicleta_id, estacao_origem_id, estacao_destino_id) continuam
    disponíveis como propriedades de leitura. O id (`id_locacao`) é dado
    pelo repositório ao guardar.
    """

    def __init__(
        self,
        usuario: "Usuario",
        bicicleta: "Bicicleta",
        origem: "Estacao",
        *,
        data_hora_inicio: Optional[datetime] = None,
        id_locacao: Optional[int] = None,
    ):
        self.id_locacao = id_locacao
        self.usuario = usuario
        self.bicicleta = bicicleta
        self.estacao_origem = origem
        self.estacao_destino: Optional["Estacao"] = None
        self.data_hora_inicio = data_hora_inicio or datetime.now()
        self.data_hora_fim: Optional[datetime] = None
        self.duracao_minutos: Optional[int] = None
        # minutos abatidos do pacote; valor_total cobre só o excedente (RN-04/RN-05)
        self.minutos_pacote = 0
        self.valor_total: Optional[float] = None
        self.em_andamento = True

    def __repr__(self) -> str:
        return (
            f"Locacao(id_locacao={self.id_locacao!r}, usuario_email={self.usuario_email!r}, "
            f"bicicleta_id={self.bicicleta_id!r}, em_andamento={self.em_andamento!r})"
        )

    # --- nomes antigos, só leitura ----------------------------------------
    @property
    def id(self) -> Optional[int]:
        return self.id_locacao

    @property
    def usuario_email(self) -> str:
        return self.usuario.email

    @property
    def bicicleta_id(self) -> int:
        return self.bicicleta.id_bicicleta

    @property
    def estacao_origem_id(self) -> int:
        return self.estacao_origem.id_estacao

    @property
    def estacao_destino_id(self) -> Optional[int]:
        return self.estacao_destino.id_estacao if self.estacao_destino is not None else None

    # ------------------------------------------------------------------
    # Tarifa (RN-04): absorvida pela Locação, sem entidade própria.
    #   valor = VALOR_BASE + minutos_a_cobrar * VALOR_POR_MINUTO
    # Minuto iniciado conta como cheio; sem nada a cobrar (0 minutos, ex.:
    # pacote cobriu tudo) o valor é 0.0 e o valor base NÃO é cobrado.
    # Configurável por TARIFA_VALOR_BASE e TARIFA_VALOR_POR_MINUTO.
    # ------------------------------------------------------------------
    VALOR_BASE: ClassVar[float] = float(os.getenv("TARIFA_VALOR_BASE", "3.00"))
    VALOR_POR_MINUTO: ClassVar[float] = float(os.getenv("TARIFA_VALOR_POR_MINUTO", "0.50"))

    @staticmethod
    def minutos_iniciados(duracao_segundos: int) -> int:
        """0 s -> 0 min; 1 s -> 1 min; 60 s -> 1 min; 61 s -> 2 min."""
        if duracao_segundos < 0:
            raise ValueError("duracao_segundos não pode ser negativa")
        return -(-duracao_segundos // 60)  # teto em aritmética inteira

    @classmethod
    def valor_por_minutos(cls, minutos_a_cobrar: int) -> float:
        """Valor de `minutos_a_cobrar` minutos já arredondados e já
        descontado o pacote."""
        if minutos_a_cobrar < 0:
            raise ValueError("duracao_min não pode ser negativa")
        if minutos_a_cobrar == 0:
            return 0.0
        return round(cls.VALOR_BASE + minutos_a_cobrar * cls.VALOR_POR_MINUTO, 2)

    # ------------------------------------------------------------------
    # Comportamento da corrida
    # ------------------------------------------------------------------
    def _momento_de_referencia(self, agora: Optional[datetime]) -> datetime:
        return agora or self.data_hora_fim or datetime.now()

    def segundos_decorridos(self, agora: Optional[datetime] = None) -> int:
        referencia = self._momento_de_referencia(agora)
        return max(0, int((referencia - self.data_hora_inicio).total_seconds()))

    def minutos_decorridos(self, agora: Optional[datetime] = None) -> int:
        return self.minutos_iniciados(self.segundos_decorridos(agora))

    def abater_saldo_pacote(
        self, minutos_disponiveis: int, agora: Optional[datetime] = None
    ) -> int:
        """Quantos minutos desta corrida o saldo informado cobre. Só calcula:
        quem consome o saldo do pacote é o PacoteService."""
        return min(self.minutos_decorridos(agora), max(0, minutos_disponiveis))

    def calcular_valor_trajeto(
        self, minutos_pacote: int = 0, agora: Optional[datetime] = None
    ) -> float:
        """Valor do excedente: minutos da corrida menos os cobertos pelo pacote."""
        return self.valor_por_minutos(self.minutos_decorridos(agora) - minutos_pacote)

    def encerrar_locacao(
        self, destino: "Estacao", minutos_pacote: int = 0,
        agora: Optional[datetime] = None,
    ) -> None:
        """Fecha a corrida na estação de destino, fixando duração, minutos
        cobertos pelo pacote e valor do excedente."""
        fim = agora or datetime.now()
        self.estacao_destino = destino
        self.data_hora_fim = fim
        self.duracao_minutos = self.minutos_decorridos(fim)
        self.minutos_pacote = minutos_pacote
        self.valor_total = self.calcular_valor_trajeto(minutos_pacote, fim)
        self.em_andamento = False

    def is_em_andamento(self) -> bool:
        return self.em_andamento
