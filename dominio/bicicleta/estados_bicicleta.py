"""
dominio/bicicleta/estados_bicicleta.py
--------------------------------------
Padrão State para o status da Bicicleta. Cada estado sabe o que a bicicleta
aceita fazer enquanto está nele e para onde ela vai em seguida; a Bicicleta
só repassa a chamada ao estado atual.

Os estados não guardam nada (são compartilhados): quem muda de estado é a
bicicleta, por `bicicleta._mudar_para(...)`.

    DISPONIVEL --iniciar_uso--> EM_USO --finalizar_uso--> DISPONIVEL
                                   |                  \\-> EM_MANUTENCAO (se havia bloqueio agendado)
    qualquer estado --enviar_para_manutencao--> EM_MANUTENCAO
    EM_MANUTENCAO --liberar_apos_reparo--> DISPONIVEL (sem avaria pendente)

Eventos que o estado atual não aceita: iniciar_uso() e finalizar_uso() levantam
ConflitoDeRegra (409); enviar_para_manutencao() em EM_MANUTENCAO e
liberar_apos_reparo() fora dela são ignorados.
"""

from abc import ABC
from typing import Callable, ClassVar, Optional

from dominio.erros import ConflitoDeRegra
from servicos_tecnicos.banco_de_dados.enums import StatusBicicleta


class EstadoBicicleta(ABC):
    status: ClassVar[StatusBicicleta]

    def apta_para_locacao(self) -> bool:
        return False

    def iniciar_uso(self, bicicleta) -> None:
        raise ConflitoDeRegra("A bicicleta não está disponível para uso")

    def finalizar_uso(self, bicicleta) -> bool:
        """Só a bicicleta EM_USO termina uma corrida; nos demais estados é erro."""
        raise ConflitoDeRegra("A bicicleta não está em uso")

    def pedir_status_manual(
        self, bicicleta, novo_status: StatusBicicleta, avaria_pendente: Callable[[], bool]
    ) -> Optional[tuple[str, str]]:
        """Troca manual (o novo status já veio validado: não é EM_USO nem o
        mesmo de agora). Devolve (anterior, novo) para a auditoria."""
        if novo_status == StatusBicicleta.DISPONIVEL and avaria_pendente():
            raise ConflitoDeRegra(
                "A bicicleta tem avaria pendente. Resolva a avaria antes de liberá-la"
            )
        anterior = str(self.status)
        bicicleta._mudar_para(novo_status)
        return anterior, str(novo_status)

    def enviar_para_manutencao(self, bicicleta) -> Optional[str]:
        anterior = str(self.status)
        bicicleta._mudar_para(StatusBicicleta.EM_MANUTENCAO)
        return anterior

    def liberar_apos_reparo(self, bicicleta, avaria_pendente: Callable[[], bool]) -> bool:
        return False


class Disponivel(EstadoBicicleta):
    status = StatusBicicleta.DISPONIVEL

    def apta_para_locacao(self) -> bool:
        return True

    def iniciar_uso(self, bicicleta) -> None:
        bicicleta._mudar_para(StatusBicicleta.EM_USO)


class EmUso(EstadoBicicleta):
    status = StatusBicicleta.EM_USO

    def finalizar_uso(self, bicicleta) -> bool:
        """Fim da corrida: volta a DISPONIVEL, ou vai para EM_MANUTENCAO se havia
        bloqueio agendado (o flag é limpo). Devolve True neste segundo caso."""
        if bicicleta.bloqueio_pendente:
            bicicleta.bloqueio_pendente = False
            bicicleta._mudar_para(StatusBicicleta.EM_MANUTENCAO)
            return True
        bicicleta._mudar_para(StatusBicicleta.DISPONIVEL)
        return False

    def pedir_status_manual(
        self, bicicleta, novo_status: StatusBicicleta, avaria_pendente: Callable[[], bool]
    ) -> Optional[tuple[str, str]]:
        """Bicicleta em corrida não muda na hora: o bloqueio fica agendado e
        é aplicado quando a corrida terminar."""
        if novo_status == StatusBicicleta.DISPONIVEL:
            raise ConflitoDeRegra(
                "A bicicleta está em corrida e não pode ser liberada agora"
            )
        if bicicleta.bloqueio_pendente:
            return None
        bicicleta.bloqueio_pendente = True
        return str(self.status), f"{StatusBicicleta.EM_MANUTENCAO} (agendado)"


class EmManutencao(EstadoBicicleta):
    status = StatusBicicleta.EM_MANUTENCAO

    def enviar_para_manutencao(self, bicicleta) -> Optional[str]:
        return None  # já está

    def liberar_apos_reparo(self, bicicleta, avaria_pendente: Callable[[], bool]) -> bool:
        if avaria_pendente():
            return False
        bicicleta._mudar_para(StatusBicicleta.DISPONIVEL)
        return True


class Bloqueada(EstadoBicicleta):
    status = StatusBicicleta.BLOQUEADA


_ESTADOS = {
    StatusBicicleta.DISPONIVEL: Disponivel(),
    StatusBicicleta.EM_USO: EmUso(),
    StatusBicicleta.EM_MANUTENCAO: EmManutencao(),
    StatusBicicleta.BLOQUEADA: Bloqueada(),
}


def estado_de(status: StatusBicicleta) -> EstadoBicicleta:
    """Estado correspondente ao status (ValueError se o valor não existe)."""
    return _ESTADOS[StatusBicicleta(status)]
