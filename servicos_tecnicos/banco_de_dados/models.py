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
from dominio.pagamento.pagamento import Pagamento
PagamentoORM = Pagamento
from dominio.pacote.pacote_minutos import PacoteMinutos
PacoteMinutosORM = PacoteMinutos
from dominio.usuario.usuario import Usuario
UsuarioORM = Usuario
from dominio.locacao.locacao import Locacao
LocacaoORM = Locacao
# ===== fim da compatibilidade =====


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


