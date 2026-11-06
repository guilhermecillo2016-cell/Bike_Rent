"""
servicos_tecnicos/banco_de_dados/models.py
----------------------------------------------
Representações internas de cada entidade guardada em memória
(equivalente às "tabelas", mas sem SQL nenhum por trás).

Convenções: a chave de cada entidade é `id` (int, gerado por
memoria.proximo_id); referências a outras entidades são campos
`<entidade>_id`. O usuário é a exceção: é identificado pelo e-mail,
então a referência a ele é `usuario_email`.
"""

import os
from dataclasses import dataclass
from typing import ClassVar, Literal, Optional
from datetime import datetime
from servicos_tecnicos.banco_de_dados.enums import (
    PapelUsuario,
    StatusAvaria,
    StatusBicicleta,
    StatusEstacao,
    StatusPagamento,
    TipoPagamento,
)


@dataclass
class UsuarioORM:
    nome: str
    email: str
    senha_hash: str
    papel: PapelUsuario
    # cpf/telefone só existem para ciclistas; administrador não os possui
    cpf: Optional[str] = None
    telefone: Optional[str] = None
    endereco: Optional[str] = None


@dataclass
class EstacaoORM:
    id: int
    nome: str
    endereco: str
    latitude: float
    longitude: float
    capacidade_total: int
    status: StatusEstacao = StatusEstacao.OPERACIONAL


@dataclass
class CartaoORM:
    token: str
    ultimos_digitos: str
    bandeira: str
    nome_titular: str
    validade: str
    tipo: str
    apelido: Optional[str] = None


@dataclass
class BicicletaORM:
    id: int
    qr_code: str
    estacao_id: Optional[int] = None
    status: StatusBicicleta = StatusBicicleta.DISPONIVEL
    bloqueio_pendente: bool = False

    def apta_para_locacao(self) -> bool:
        return self.status == StatusBicicleta.DISPONIVEL


@dataclass
class LocacaoORM:
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
        self, destino: "EstacaoORM", minutos_pacote: int = 0,
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


@dataclass
class PagamentoORM:
    """Paga uma corrida OU a compra de um pacote: exatamente um entre
    locacao_id e pacote_id deve estar preenchido (validado no service)."""

    id: int
    valor: float
    tipo: TipoPagamento
    data_hora: datetime
    status: StatusPagamento = StatusPagamento.PENDENTE
    locacao_id: Optional[int] = None
    pacote_id: Optional[int] = None
    token_cartao: Optional[str] = None
    qr_code_pix: Optional[str] = None


@dataclass
class ReporteAvariaORM:
    id: int
    descricao: str
    data_hora: datetime
    usuario_email: str
    bicicleta_id: int
    status: StatusAvaria = StatusAvaria.PENDENTE

    def resolver(self) -> None:
        self.status = StatusAvaria.RESOLVIDO



@dataclass
class ComprovanteORM:
    id: int
    data_emissao: datetime
    resumo_trajeto: str
    tarifa_aplicada: float
    locacao_id: int
    # None quando o pacote cobriu a corrida inteira (não houve cobrança)
    pagamento_id: Optional[int] = None


@dataclass
class EventoAuditoriaORM:
    """Histórico de alterações manuais de status (UC2, pós-condição 3).
    Não consta no diagrama de classes; ver issue [C7]."""

    id: int
    data_hora: datetime
    usuario_email: str
    tipo_entidade: Literal["BICICLETA", "ESTACAO"]
    entidade_id: int
    status_anterior: str
    status_novo: str


@dataclass
class PacoteMinutosORM:
    id: int
    usuario_email: str
    minutos_totais: int
    minutos_restantes: int
    data_validade: datetime
    # False até o pagamento da compra ser aprovado
    ativo: bool = False

