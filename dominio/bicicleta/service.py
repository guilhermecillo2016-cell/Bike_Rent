"""
dominio/bicicleta/service.py
------------------------------
Regras de negócio do domínio Bicicleta: cadastro, busca por QR Code e
troca de status. É daqui que as outras trilhas consomem a bicicleta:

- get_by_qr(qr)         -> validação do QR Code (B2)
- set_status(id, st)    -> transições da corrida (B3/B5/B6)
- apta_para_locacao()   -> método do próprio Bicicleta

A localização de uma bicicleta é só o seu estacao_id; a lista e a
contagem de vagas da estação saem de consultas por esse campo.
"""

from typing import Optional

from fastapi import HTTPException, status as http

from dominio.auditoria import service as auditoria_service
from dominio.bicicleta.schemas import BicicletaCreate, BicicletaPublic
from dominio.estacao import service as estacao_service
from servicos_tecnicos.banco_de_dados.fabrica import repositorios
from servicos_tecnicos.banco_de_dados.enums import StatusAvaria, StatusBicicleta
from dominio.bicicleta.bicicleta import Bicicleta


def to_public(bicicleta: Bicicleta) -> BicicletaPublic:
    return BicicletaPublic(
        id=bicicleta.id,
        qr_code=bicicleta.qr_code,
        status=bicicleta.status,
        estacao_id=bicicleta.estacao_id,
        bloqueio_pendente=bicicleta.bloqueio_pendente,
    )


def cadastrar_bicicleta(dados: BicicletaCreate) -> Bicicleta:
    """Cadastra a bicicleta já estacionada na estação, ocupando uma vaga.

    404 se a estação não existe; 409 se não está operacional ou está lotada.
    """
    estacao = estacao_service.exigir_vaga_livre(dados.estacao_id)
    return repositorios().bicicleta.create(estacao)


def obter_bicicleta(bicicleta_id: int) -> Bicicleta:
    bicicleta = repositorios().bicicleta.get_by_id(bicicleta_id)
    if bicicleta is None:
        raise HTTPException(
            status_code=http.HTTP_404_NOT_FOUND,
            detail="Bicicleta não encontrada",
        )
    return bicicleta


def get_by_qr(qr_code: str) -> Bicicleta:
    """Bicicleta dona do QR Code lido (extensão 3a do UC1: QR inválido -> 404)."""
    bicicleta = repositorios().bicicleta.get_by_qr((qr_code or "").strip())
    if bicicleta is None:
        raise HTTPException(
            status_code=http.HTTP_404_NOT_FOUND,
            detail="Bicicleta não encontrada. Tente escanear o QR Code novamente.",
        )
    return bicicleta


def set_status(bicicleta_id: int, novo_status: StatusBicicleta) -> Bicicleta:
    """Troca interna de status, sem auditoria (usada pelo fluxo da corrida).

    A alteração manual feita por administrador/operador, com registro de
    auditoria e a regra da bicicleta em uso, é da A5 e usa esta função.
    """
    bicicleta = obter_bicicleta(bicicleta_id)
    bicicleta.set_status(novo_status)  # valor inválido -> ValueError
    return repositorios().bicicleta.salvar(bicicleta)


def _tem_avaria_pendente(bicicleta_id: int) -> bool:
    avarias = repositorios().avaria.list_by_bicicleta(bicicleta_id)
    return any(a.status != StatusAvaria.RESOLVIDO for a in avarias)
tem_avaria_pendente = _tem_avaria_pendente

def alterar_status_manual(
    bicicleta_id: int, novo_status: StatusBicicleta, usuario_email: str
) -> Bicicleta:
    """Troca o status à mão (administrador ou operador) e registra na auditoria.

    Bicicleta em corrida não muda na hora: o bloqueio fica agendado
    (bloqueio_pendente) e é aplicado quando a corrida terminar.
    404 se não existe; 400 se pedirem EM_USO; 409 se tentarem liberar uma
    bicicleta em corrida ou com avaria pendente.
    """
    bicicleta = obter_bicicleta(bicicleta_id)
    mudanca = bicicleta.alterar_status_manual(
        StatusBicicleta(novo_status), lambda: _tem_avaria_pendente(bicicleta.id)
    )
    repositorios().bicicleta.salvar(bicicleta)  # status ou bloqueio agendado
    if mudanca is not None:
        anterior, novo = mudanca
        auditoria_service.registrar(
            usuario_email, "BICICLETA", bicicleta.id, anterior, novo
        )
    return bicicleta


def finalizar_uso(bicicleta_id: int) -> Bicicleta:
    """Chamada ao encerrar a corrida: a bicicleta volta a DISPONIVEL, ou vai
    para EM_MANUTENCAO se houver bloqueio agendado (que então é limpo)."""
    bicicleta = obter_bicicleta(bicicleta_id)
    bloqueada = bicicleta.finalizar_uso()
    repositorios().bicicleta.salvar(bicicleta)
    if bloqueada:
        auditoria_service.registrar(
            "sistema", "BICICLETA", bicicleta.id,
            str(StatusBicicleta.EM_USO), str(StatusBicicleta.EM_MANUTENCAO),
        )
    return bicicleta


def listar_bicicletas(
    status: Optional[StatusBicicleta] = None,
    estacao_id: Optional[int] = None,
) -> list[Bicicleta]:
    bicicletas = repositorios().bicicleta.list_all()
    if status is not None:
        bicicletas = [b for b in bicicletas if b.status == status]
    if estacao_id is not None:
        bicicletas = [b for b in bicicletas if b.estacao_id == estacao_id]
    return bicicletas


class BicicletaIndisponivel(Exception):
    """Bicicleta existe, mas não está apta (EM_USO, EM_MANUTENCAO ou
    BLOQUEADA). Carrega as alternativas da mesma estação (extensão 3b)."""

    def __init__(self, bicicleta: Bicicleta, sugestoes : list[Bicicleta]):
        self.bicicleta = bicicleta
        self.sugestoes = sugestoes

def validar_qr(qr_code: str) -> Bicicleta:
    bicicleta = get_by_qr(qr_code)

    if not bicicleta.apta_para_locacao():
        sugestoes = []
        if bicicleta.estacao_id is not None: #EM_USO não tem estação
            sugestoes = [b for b in repositorios().bicicleta.list_by_estacao(bicicleta.estacao_id) if b.id != bicicleta.id and b.apta_para_locacao()]
        raise BicicletaIndisponivel(bicicleta, sugestoes)
    return bicicleta