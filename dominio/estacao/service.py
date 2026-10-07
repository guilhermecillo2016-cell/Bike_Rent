"""
dominio/estacao/service.py
----------------------------
Regras de negócio do domínio Estacao: cadastro (feito por um
administrador) e listagem das estações disponíveis no sistema.

A validação de faixa de latitude/longitude e de capacidade > 0 já
acontece no schema (EstacaoCreate); aqui ficam regras adicionais de
negócio.
"""

from servicos_tecnicos.banco_de_dados import repository_bicicleta
from servicos_tecnicos.banco_de_dados import repository_estacao as repo
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
