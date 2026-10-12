"""
dominio/bicicleta/service.py
------------------------------
Regras de negócio do domínio Bicicleta: cadastro, busca por QR Code e
troca de status. É daqui que as outras trilhas consomem a bicicleta:

- get_by_qr(qr)         -> validação do QR Code (B2)
- set_status(id, st)    -> transições da corrida (B3/B5/B6)
- apta_para_locacao()   -> método do próprio BicicletaORM

A localização de uma bicicleta é só o seu estacao_id; a lista e a
contagem de vagas da estação saem de consultas por esse campo.
"""

from typing import Optional

from fastapi import HTTPException, status as http

from dominio import bicicleta
from dominio.bicicleta.schemas import BicicletaCreate, BicicletaPublic
from dominio.estacao import service as estacao_service
from servicos_tecnicos.banco_de_dados import repository_bicicleta as repo
from servicos_tecnicos.banco_de_dados.enums import StatusBicicleta
from servicos_tecnicos.banco_de_dados.models import BicicletaORM


def to_public(bicicleta: BicicletaORM) -> BicicletaPublic:
    return BicicletaPublic(
        id=bicicleta.id,
        qr_code=bicicleta.qr_code,
        status=bicicleta.status,
        estacao_id=bicicleta.estacao_id,
        bloqueio_pendente=bicicleta.bloqueio_pendente,
    )


def cadastrar_bicicleta(dados: BicicletaCreate) -> BicicletaORM:
    """Cadastra a bicicleta já estacionada na estação, ocupando uma vaga.

    404 se a estação não existe; 409 se não está operacional ou está lotada.
    """
    estacao_service.exigir_vaga_livre(dados.estacao_id)
    return repo.create(dados.estacao_id)


def obter_bicicleta(bicicleta_id: int) -> BicicletaORM:
    bicicleta = repo.get_by_id(bicicleta_id)
    if bicicleta is None:
        raise HTTPException(
            status_code=http.HTTP_404_NOT_FOUND,
            detail="Bicicleta não encontrada",
        )
    return bicicleta


def get_by_qr(qr_code: str) -> BicicletaORM:
    """Bicicleta dona do QR Code lido (extensão 3a do UC1: QR inválido -> 404)."""
    bicicleta = repo.get_by_qr((qr_code or "").strip())
    if bicicleta is None:
        raise HTTPException(
            status_code=http.HTTP_404_NOT_FOUND,
            detail="Bicicleta não encontrada. Tente escanear o QR Code novamente.",
        )
    return bicicleta


def set_status(bicicleta_id: int, novo_status: StatusBicicleta) -> BicicletaORM:
    """Troca interna de status, sem auditoria (usada pelo fluxo da corrida).

    A alteração manual feita por administrador/operador, com registro de
    auditoria e a regra da bicicleta em uso, é da A5 e usa esta função.
    """
    bicicleta = obter_bicicleta(bicicleta_id)
    bicicleta.status = StatusBicicleta(novo_status)  # valor inválido -> ValueError
    return bicicleta


def listar_bicicletas(
    status: Optional[StatusBicicleta] = None,
    estacao_id: Optional[int] = None,
) -> list[BicicletaORM]:
    bicicletas = repo.list_all()
    if status is not None:
        bicicletas = [b for b in bicicletas if b.status == status]
    if estacao_id is not None:
        bicicletas = [b for b in bicicletas if b.estacao_id == estacao_id]
    return bicicletas


class BicicletaIndisponivel(Exception):
    """Bicicleta existe, mas não está apta (EM_USO, EM_MANUTENCAO ou
    BLOQUEADA). Carrega as alternativas da mesma estação (extensão 3b)."""

    def __init__(self, bicicleta: BicicletaORM, sugestoes : list[BicicletaORM]):
        self.bicicleta = bicicleta
        self.segestoes = sugestoes

def validar_qr(qr_code: str) -> BicicletaORM:
    bicicleta = get_by_qr(qr_code)

    if not bicicleta.apta_para_locacao():
        sugestoes = []
        if bicicleta.estacao_id is not None: #EM_USO não tem estação
            sugestoes = [b for b in repo.list_by_estacao(bicicleta.estacao_id) if b.id != bicicleta.id and b.apta_para_locacao()]
        raise BicicletaIndisponivel(bicicleta, sugestoes)
    return bicicleta