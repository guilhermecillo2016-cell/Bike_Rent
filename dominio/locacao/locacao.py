"""
dominio/locacao/locacao.py
----------------------------------
Classe `Locacao` do diagrama: a corrida. A tarifa (RN-04) é regra dela.
"""

import os
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, ClassVar, Optional

if TYPE_CHECKING:
    from dominio.estacao.estacao import Estacao


@dataclass
class Locacao:
    id: int
    usuario_email: str
    bicicleta_id: int
    estacao_origem_id: int
    data_hora_inicio: datetime
    estacao_destino_id: Optional[int] = None
    data_hora_fim: Optional[datetime] = None
    duracao_minutos: Optional[int] = None
    # minutos abatidos do pacote; valor_total cobre só o excedente (RN-04/RN-05)
    minutos_pacote: int = 0
    valor_total: Optional[float] = None
    em_andamento: bool = True

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
        self.estacao_destino_id = destino.id
        self.data_hora_fim = fim
        self.duracao_minutos = self.minutos_decorridos(fim)
        self.minutos_pacote = minutos_pacote
        self.valor_total = self.calcular_valor_trajeto(minutos_pacote, fim)
        self.em_andamento = False

    def is_em_andamento(self) -> bool:
        return self.em_andamento
