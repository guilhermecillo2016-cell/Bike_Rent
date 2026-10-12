"""
dominio/avaria/service.py
---------------------------
Reporte de avaria (RF-14, RN-09, RNF-10) e resolução pelo operador.
"""

from typing import Optional

from fastapi import HTTPException, status as http

from dominio.auditoria import service as auditoria_service
from dominio.avaria.schemas import AvariaPublic
from dominio.bicicleta import service as bicicleta_service
from servicos_tecnicos.banco_de_dados import repository_avaria as repo
from servicos_tecnicos.banco_de_dados.enums import StatusAvaria, StatusBicicleta
from servicos_tecnicos.banco_de_dados.models import ReporteAvariaORM


def to_public(a: ReporteAvariaORM) -> AvariaPublic:
    return AvariaPublic(
        id=a.id, descricao=a.descricao, data_hora=a.data_hora,
        usuario_email=a.usuario_email, bicicleta_id=a.bicicleta_id, status=a.status,
    )


def reportar_avaria(usuario_email: str, bicicleta_id: int, descricao: str) -> ReporteAvariaORM:
    """Grava o reporte e põe a bicicleta em EM_MANUTENCAO na hora (RN-09).
    Como só DISPONIVEL é apta, ela some da estação e o QR passa a dar 409."""
    descricao = (descricao or "").strip()
    if not descricao:
        raise HTTPException(
            status_code=http.HTTP_400_BAD_REQUEST,
            detail="Descreva o problema da bicicleta",
        )
    bicicleta = bicicleta_service.obter_bicicleta(bicicleta_id)
    avaria = repo.create(descricao, usuario_email, bicicleta_id)

    if bicicleta.status != StatusBicicleta.EM_MANUTENCAO:
        anterior = str(bicicleta.status)
        bicicleta.status = StatusBicicleta.EM_MANUTENCAO
        auditoria_service.registrar(
            usuario_email, "BICICLETA", bicicleta.id,
            anterior, str(StatusBicicleta.EM_MANUTENCAO),
        )
    return avaria


def obter_avaria(avaria_id: int) -> ReporteAvariaORM:
    avaria = repo.get_by_id(avaria_id)
    if avaria is None:
        raise HTTPException(
            status_code=http.HTTP_404_NOT_FOUND,
            detail="Avaria não encontrada",
        )
    return avaria


def listar_avarias(status: Optional[StatusAvaria] = None) -> list[ReporteAvariaORM]:
    avarias = repo.list_all()
    if status is not None:
        avarias = [a for a in avarias if a.status == status]
    return sorted(avarias, key=lambda a: a.id, reverse=True)


def resolver_avaria(avaria_id: int, operador_email: str) -> ReporteAvariaORM:
    """Marca como RESOLVIDO. A bicicleta só volta a DISPONIVEL se estiver
    EM_MANUTENCAO e não houver outra avaria PENDENTE/EM_REPARO; se estiver
    BLOQUEADA (por outro motivo), continua bloqueada.
    404 se não existe; 409 se já estava resolvida."""
    avaria = obter_avaria(avaria_id)
    if avaria.status == StatusAvaria.RESOLVIDO:
        raise HTTPException(
            status_code=http.HTTP_409_CONFLICT,
            detail="Esta avaria já foi resolvida",
        )
    avaria.resolver()

    bicicleta = bicicleta_service.obter_bicicleta(avaria.bicicleta_id)
    if (
        bicicleta.status == StatusBicicleta.EM_MANUTENCAO
        and not bicicleta_service.tem_avaria_pendente(bicicleta.id)
    ):
        bicicleta.status = StatusBicicleta.DISPONIVEL
        auditoria_service.registrar(
            operador_email, "BICICLETA", bicicleta.id,
            str(StatusBicicleta.EM_MANUTENCAO), str(StatusBicicleta.DISPONIVEL),
        )
    return avaria