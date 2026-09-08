"""
dominio/estacao/service.py
----------------------------
Regras de negócio do domínio Estacao: cadastro (feito por um
administrador) e listagem das estações disponíveis no sistema.

A validação de faixa de latitude/longitude e de capacidade > 0 já
acontece no schema (EstacaoCreate); aqui ficam regras adicionais de
negócio.
"""

from servicos_tecnicos.banco_de_dados import repository_estacao as repo
from servicos_tecnicos.banco_de_dados.models import EstacaoORM
from dominio.estacao.schemas import EstacaoCreate


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
