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
from dataclasses import dataclass, field
from typing import Callable, ClassVar, Literal, Optional
from datetime import datetime
from dominio.erros import ConflitoDeRegra, RequisicaoInvalida
from dominio.geolocalizacao.geolocalizacao import Geolocalizacao
from servicos_tecnicos.banco_de_dados import memoria
from servicos_tecnicos.banco_de_dados.estados_bicicleta import EstadoBicicleta, estado_de
from servicos_tecnicos.seguranca import conferir_senha
from servicos_tecnicos.banco_de_dados.enums import (
    PapelUsuario,
    StatusAvaria,
    StatusBicicleta,
    StatusEstacao,
    StatusPagamento,
    TipoPagamento,
)


# ===== compatibilidade: classes que já saíram deste arquivo =====
from dominio.pagamento.cartao import Cartao
CartaoORM = Cartao
from dominio.auditoria.evento_auditoria import EventoAuditoria
EventoAuditoriaORM = EventoAuditoria
from dominio.avaria.reporte_avaria import ReporteAvaria
ReporteAvariaORM = ReporteAvaria
from dominio.comprovante.comprovante_viagem import ComprovanteViagem
ComprovanteORM = ComprovanteViagem
# ===== fim da compatibilidade =====


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

    def autenticar(self, senha: str) -> bool:
        """Confere a senha em texto contra o hash guardado."""
        return conferir_senha(senha, self.senha_hash)

    def get_papel(self) -> PapelUsuario:
        return self.papel

    def possui_cartao_valido(self) -> bool:
        """RN-06: tem ao menos um cartão de crédito vinculado."""
        return any(c.tipo == "CARTAO_CREDITO" for c in memoria.cartoes.get(self.email, []))

    def tem_pacote_minutos_ativo(self, agora: Optional[datetime] = None) -> bool:
        """Tem pacote ativo, com saldo e dentro da validade."""
        agora = agora or datetime.now()
        return any(
            p.usuario_email == self.email
            and p.ativo
            and p.minutos_restantes > 0
            and p.data_validade > agora
            for p in memoria.pacotes.values()
        )


@dataclass
class EstacaoORM:
    """Estação. É a ÚNICA dona da associação com as bicicletas: a lista
    `bicicletas` é a fonte da verdade e `Bicicleta.estacao` só espelha."""

    id: int
    nome: str
    endereco: str
    # Objeto de valor: no banco vira as colunas latitude e longitude.
    localizacao: Geolocalizacao
    capacidade_total: int
    status: StatusEstacao = StatusEstacao.OPERACIONAL
    bicicletas: list = field(default_factory=list, repr=False, compare=False)

    @property
    def latitude(self) -> float:
        return self.localizacao.latitude

    @property
    def longitude(self) -> float:
        return self.localizacao.longitude

    def distancia_ate_em_metros(self, outra: "EstacaoORM") -> float:
        return self.localizacao.calcular_distancia_em_metros(outra.localizacao)

    @property
    def vagas_disponiveis(self) -> int:
        """Derivado: capacidade menos as bicicletas que estão aqui."""
        return self.capacidade_total - len(self.bicicletas)

    def possui_vaga_livre(self) -> bool:
        return self.status == StatusEstacao.OPERACIONAL and self.vagas_disponiveis > 0

    def quantidade_bicicletas_disponiveis(self) -> int:
        return sum(1 for b in self.bicicletas if b.apta_para_locacao())

    def possui_bicicleta_disponivel(self) -> bool:
        return self.quantidade_bicicletas_disponiveis() > 0

    def exigir_vaga_livre(self) -> None:
        """409 se não está OPERACIONAL (bloqueada ou em manutenção não recebe
        nem libera bicicletas) ou se está lotada."""
        if self.status != StatusEstacao.OPERACIONAL:
            raise ConflitoDeRegra("A estação não está operacional")
        if self.vagas_disponiveis <= 0:
            raise ConflitoDeRegra("A estação está lotada")

    def adicionar_bicicleta(self, bicicleta: "BicicletaORM") -> None:
        """Guarda a bicicleta na lista SEM checar vaga nem status (usado no
        cadastro; quem quer a regra completa usa alocar_bicicleta)."""
        self.bicicletas.append(bicicleta)
        bicicleta._entrar_na_estacao(self)

    def alocar_bicicleta(self, bicicleta: "BicicletaORM") -> None:
        """Estaciona a bicicleta aqui. 409 se a estação não aceita ou se a
        bicicleta já está em uma estação."""
        self.exigir_vaga_livre()
        if bicicleta.estacao is not None:
            raise ConflitoDeRegra("A bicicleta já está em uma estação")
        self.adicionar_bicicleta(bicicleta)

    def remover_bicicleta(self, bicicleta: "BicicletaORM") -> None:
        """Tira a bicicleta daqui. 409 se a estação não está operacional ou
        se a bicicleta não está nela."""
        if self.status != StatusEstacao.OPERACIONAL:
            raise ConflitoDeRegra("A estação não está operacional")
        if not any(b is bicicleta for b in self.bicicletas):
            raise ConflitoDeRegra("A bicicleta não está nesta estação")
        self.bicicletas[:] = [b for b in self.bicicletas if b is not bicicleta]
        bicicleta._sair_da_estacao()

    def set_status(self, novo_status: StatusEstacao) -> None:
        self.status = StatusEstacao(novo_status)


class BicicletaORM:
    """Bicicleta. O status é controlado por um objeto de estado (padrão State,
    ver estados_bicicleta.py); `status` continua sendo lido e atribuído como
    um atributo comum."""

    def __init__(
        self,
        id: int,
        qr_code: str,
        status: StatusBicicleta = StatusBicicleta.DISPONIVEL,
        bloqueio_pendente: bool = False,
    ):
        self.id = id
        self.qr_code = qr_code
        self.bloqueio_pendente = bloqueio_pendente
        self._estado: EstadoBicicleta = estado_de(status)
        # Espelho da lista da Estacao: só a própria Estacao mexe nisto
        # (adicionar_bicicleta / remover_bicicleta).
        self._estacao: Optional[EstacaoORM] = None

    def __repr__(self) -> str:
        return (
            f"BicicletaORM(id={self.id!r}, qr_code={self.qr_code!r}, "
            f"status={self.status!r}, bloqueio_pendente={self.bloqueio_pendente!r})"
        )

    # --- Associação com a estação (espelho) ---------------------------
    @property
    def estacao(self) -> Optional[EstacaoORM]:
        return self._estacao

    @property
    def estacao_id(self) -> Optional[int]:
        return self._estacao.id if self._estacao is not None else None

    def _entrar_na_estacao(self, estacao: EstacaoORM) -> None:
        self._estacao = estacao

    def _sair_da_estacao(self) -> None:
        self._estacao = None

    # --- Status (State) -------------------------------------------------
    @property
    def status(self) -> StatusBicicleta:
        return self._estado.status

    @status.setter
    def status(self, novo_status: StatusBicicleta) -> None:
        self._estado = estado_de(novo_status)

    def _mudar_para(self, novo_status: StatusBicicleta) -> None:
        """Chamado pelos estados ao trocar de estado."""
        self.status = novo_status

    def apta_para_locacao(self) -> bool:
        return self._estado.apta_para_locacao()

    def get_status(self) -> StatusBicicleta:
        return self.status

    def set_status(self, novo_status: StatusBicicleta) -> None:
        """Troca direta, sem regra (fluxos internos). Valor inválido -> ValueError."""
        self.status = novo_status

    # --- Transições: quem decide é o estado atual ------------------------
    def iniciar_uso(self) -> None:
        """Começa a corrida: só uma bicicleta DISPONIVEL pode entrar em uso."""
        self._estado.iniciar_uso(self)

    def finalizar_uso(self) -> bool:
        """Fim da corrida: volta a DISPONIVEL, ou vai para EM_MANUTENCAO se
        havia bloqueio agendado (que então é limpo). Devolve True nesse
        segundo caso, para o service registrar a auditoria."""
        return self._estado.finalizar_uso(self)

    def alterar_status_manual(
        self, novo_status: StatusBicicleta, avaria_pendente: Callable[[], bool]
    ) -> Optional[tuple[str, str]]:
        """Troca manual feita por administrador/operador.

        Bicicleta em corrida não muda na hora: o bloqueio fica agendado
        (bloqueio_pendente). 400 se pedirem EM_USO; 409 se tentarem liberar
        uma bicicleta em corrida ou com avaria pendente. Devolve
        (status_anterior, status_novo) para a auditoria, ou None se nada mudou.
        """
        novo_status = StatusBicicleta(novo_status)

        if novo_status == StatusBicicleta.EM_USO:
            raise RequisicaoInvalida("Uma bicicleta só entra em uso por uma locação")
        if novo_status == self.status:
            return None
        return self._estado.pedir_status_manual(self, novo_status, avaria_pendente)

    def enviar_para_manutencao(self) -> Optional[str]:
        """Reporte de avaria (RN-09): vai para EM_MANUTENCAO na hora. Devolve o
        status anterior, ou None se já estava em manutenção."""
        return self._estado.enviar_para_manutencao(self)

    def liberar_apos_reparo(self, avaria_pendente: Callable[[], bool]) -> bool:
        """Avaria resolvida: só volta a DISPONIVEL se estiver EM_MANUTENCAO e
        não houver outra avaria pendente (BLOQUEADA continua bloqueada)."""
        return self._estado.liberar_apos_reparo(self, avaria_pendente)


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
class PacoteMinutosORM:
    id: int
    usuario_email: str
    minutos_totais: int
    minutos_restantes: int
    data_validade: datetime
    # False até o pagamento da compra ser aprovado
    ativo: bool = False

