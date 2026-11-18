"""
dominio/bicicleta/bicicleta.py
--------------------------------------
Classe `Bicicleta` do diagrama. O status usa o padrão State
(estados_bicicleta.py, na mesma pasta).
"""

from typing import TYPE_CHECKING, Callable, Optional

from dominio.bicicleta.estados_bicicleta import EstadoBicicleta, estado_de
from dominio.erros import RequisicaoInvalida
from servicos_tecnicos.banco_de_dados.enums import StatusBicicleta

if TYPE_CHECKING:
    from dominio.estacao.estacao import Estacao


class Bicicleta:
    """Bicicleta. O status é controlado por um objeto de estado (padrão State,
    ver estados_bicicleta.py); `status` continua sendo lido e atribuído como
    um atributo comum."""

    def __init__(
        self,
        id_bicicleta: int,
        qr_code: str,
        status: StatusBicicleta = StatusBicicleta.DISPONIVEL,
        bloqueio_pendente: bool = False,
    ):
        self.id_bicicleta = id_bicicleta
        self.qr_code = qr_code
        self.bloqueio_pendente = bloqueio_pendente
        self._estado: EstadoBicicleta = estado_de(status)
        # Espelho da lista da Estacao: só a própria Estacao mexe nisto
        # (adicionar_bicicleta / remover_bicicleta).
        self._estacao: Optional["Estacao"] = None

    @property
    def id(self) -> int:
        return self.id_bicicleta

    def __repr__(self) -> str:
        return (
            f"Bicicleta(id_bicicleta={self.id_bicicleta!r}, qr_code={self.qr_code!r}, "
            f"status={self.status!r}, bloqueio_pendente={self.bloqueio_pendente!r})"
        )

    # --- Associação com a estação (espelho) ---------------------------
    @property
    def estacao(self) -> Optional["Estacao"]:
        return self._estacao

    @property
    def estacao_id(self) -> Optional[int]:
        return self._estacao.id if self._estacao is not None else None

    def _entrar_na_estacao(self, estacao: "Estacao") -> None:
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
        """Fim da corrida (só aceito com a bicicleta EM_USO; nos outros estados
        levanta ConflitoDeRegra): volta a DISPONIVEL, ou vai para EM_MANUTENCAO se
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
