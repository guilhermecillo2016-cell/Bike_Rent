"""
dominio/estacao/service.py
----------------------------
Regras de negócio do domínio Estacao: cadastro (feito por um
administrador) e listagem das estações disponíveis no sistema.

A validação de faixa de latitude/longitude e de capacidade > 0 já
acontece no schema (EstacaoCreate); aqui ficam regras adicionais de
negócio.
"""

from fastapi import HTTPException, status as http

from servicos_tecnicos.banco_de_dados import repository_bicicleta
from servicos_tecnicos.banco_de_dados import repository_estacao as repo
from servicos_tecnicos.banco_de_dados.enums import StatusEstacao
from servicos_tecnicos.banco_de_dados.models import EstacaoORM
from dominio.estacao.schemas import EstacaoCreate, EstacaoPublic

def vagas_disponiveis(estacao: EstacaoORM) -> int:
    """Vagas livres = capacidade - bicicletas cujo estacao_id é esta estação."""
    ocupadas = len(repository_bicicleta.list_by_estacao(estacao.id))
    return estacao.capacidade_total - ocupadas


def to_public(estacao: EstacaoORM) -> EstacaoPublic:
    return EstacaoPublic(
        id=estacao.id,
        nome=estacao.nome,
        endereco=estacao.endereco,
        latitude=estacao.latitude,
        longitude=estacao.longitude,
        capacidade_total=estacao.capacidade_total,
        vagas_disponiveis=vagas_disponiveis(estacao),
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
