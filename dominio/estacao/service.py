"""
dominio/estacao/service.py
----------------------------
Regras de negócio do domínio Estacao: cadastro (feito por um
administrador) e listagem das estações disponíveis no sistema.

A validação de faixa de latitude/longitude e de capacidade > 0 já
acontece no schema (EstacaoCreate); aqui ficam regras adicionais de
negócio.
"""
from math import asin, cos, radians, sin, sqrt

from fastapi import HTTPException, status as http

from dominio.auditoria import service as auditoria_service
from servicos_tecnicos.banco_de_dados import repository_bicicleta
from servicos_tecnicos.banco_de_dados import repository_estacao as repo
from servicos_tecnicos.banco_de_dados.enums import StatusEstacao
from servicos_tecnicos.banco_de_dados.models import BicicletaORM, EstacaoORM
from dominio.estacao.schemas import EstacaoCreate, EstacaoPublic


def vagas_disponiveis(estacao: EstacaoORM) -> int:
    """Vagas livres = capacidade - bicicletas cujo estacao_id é esta estação."""
    ocupadas = len(repository_bicicleta.list_by_estacao(estacao.id))
    return estacao.capacidade_total - ocupadas


def bicicletas_disponiveis(estacao: EstacaoORM) -> int:
    bicicletas = repository_bicicleta.list_by_estacao(estacao.id)
    return sum(1 for b in bicicletas if b.apta_para_locacao())


def to_public(estacao: EstacaoORM) -> EstacaoPublic:
    return EstacaoPublic(
        id=estacao.id,
        nome=estacao.nome,
        endereco=estacao.endereco,
        latitude=estacao.latitude,
        longitude=estacao.longitude,
        capacidade_total=estacao.capacidade_total,
        vagas_disponiveis=vagas_disponiveis(estacao),
        bicicletas_disponiveis=bicicletas_disponiveis(estacao),
        status=estacao.status,
    )


def obter_estacao(estacao_id: int) -> EstacaoORM:
    """Devolve a estação ou levanta 404."""
    estacao = repo.get_by_id(estacao_id)
    if estacao is None:
        raise HTTPException(
            status_code=http.HTTP_404_NOT_FOUND,
            detail="Estação não encontrada",
        )
    return estacao


def exigir_vaga_livre(estacao_id: int) -> EstacaoORM:
    """Garante que a estação pode receber uma bicicleta agora.

    404 se não existe; 409 se não está OPERACIONAL (bloqueada ou em
    manutenção não recebe nem libera bicicletas) ou se está lotada.
    Devolve a estação.
    """
    estacao = obter_estacao(estacao_id)
    if estacao.status != StatusEstacao.OPERACIONAL:
        raise HTTPException(
            status_code=http.HTTP_409_CONFLICT,
            detail="A estação não está operacional",
        )
    if vagas_disponiveis(estacao) <= 0:
        raise HTTPException(
            status_code=http.HTTP_409_CONFLICT,
            detail="A estação está lotada",
        )
    return estacao


def possui_vaga_livre(estacao_id: int) -> bool:
    """Versão sim/não de exigir_vaga_livre (404 se a estação não existe)."""
    estacao = obter_estacao(estacao_id)
    return (
        estacao.status == StatusEstacao.OPERACIONAL
        and vagas_disponiveis(estacao) > 0
    )


def alocar_bicicleta(estacao_id: int, bicicleta_id: int) -> BicicletaORM:
    """Estaciona a bicicleta na estação. 404 se algum dos dois não existe;
    409 se a estação não aceita ou se a bicicleta já está em outra."""
    exigir_vaga_livre(estacao_id)

    bicicleta = repository_bicicleta.get_by_id(bicicleta_id)
    if bicicleta is None:
        raise HTTPException(
            status_code=http.HTTP_404_NOT_FOUND,
            detail="Bicicleta não encontrada",
        )
    if bicicleta.estacao_id is not None:
        raise HTTPException(
            status_code=http.HTTP_409_CONFLICT,
            detail="A bicicleta já está em uma estação",
        )

    bicicleta.estacao_id = estacao_id
    return bicicleta


def remover_bicicleta(bicicleta_id: int) -> BicicletaORM:
    """Tira a bicicleta da estação. 404 se ela não existe; 409 se não está em
    nenhuma estação ou se a estação dela não está operacional."""
    bicicleta = repository_bicicleta.get_by_id(bicicleta_id)
    if bicicleta is None:
        raise HTTPException(
            status_code=http.HTTP_404_NOT_FOUND,
            detail="Bicicleta não encontrada",
        )
    if bicicleta.estacao_id is None:
        raise HTTPException(
            status_code=http.HTTP_409_CONFLICT,
            detail="A bicicleta não está em nenhuma estação",
        )

    estacao = obter_estacao(bicicleta.estacao_id)
    if estacao.status != StatusEstacao.OPERACIONAL:
        raise HTTPException(
            status_code=http.HTTP_409_CONFLICT,
            detail="A estação não está operacional",
        )

    bicicleta.estacao_id = None
    return bicicleta


def alterar_status_manual(
    estacao_id: int, novo_status: StatusEstacao, usuario_email: str
) -> EstacaoORM:
    """Troca o status da estação à mão e registra na auditoria. 404 se não existe."""
    estacao = obter_estacao(estacao_id)
    novo_status = StatusEstacao(novo_status)
    if novo_status == estacao.status:
        return estacao

    anterior = str(estacao.status)
    estacao.status = novo_status
    auditoria_service.registrar(
        usuario_email, "ESTACAO", estacao.id, anterior, str(novo_status)
    )
    return estacao


def criar_estacao(dados: EstacaoCreate) -> EstacaoORM:
    return repo.create(
        nome=dados.nome,
        endereco=dados.endereco,
        latitude=dados.latitude,
        longitude=dados.longitude,
        capacidade_total=dados.capacidade_total,
    )


def listar_estacoes() -> list[EstacaoORM]:
    return repo.list_all()


def _distancia_km(a: EstacaoORM, b: EstacaoORM) -> float:
    """Distância em linha reta (haversine) entre duas estações."""
    lat1, lon1, lat2, lon2 = map(radians, (a.latitude, a.longitude, b.latitude, b.longitude))
    h = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * asin(sqrt(h))


def estacoes_proximas_com_vaga(referencia: EstacaoORM, limite: int = 3) -> list[EstacaoORM]:
    """Estações OPERACIONAIS com vaga livre, da mais perto para a mais longe."""
    candidatas = [
        e for e in repo.list_all()
        if e.id != referencia.id
        and e.status == StatusEstacao.OPERACIONAL
        and vagas_disponiveis(e) > 0
    ]
    candidatas.sort(key=lambda e: _distancia_km(referencia, e))
    return candidatas[:limite]