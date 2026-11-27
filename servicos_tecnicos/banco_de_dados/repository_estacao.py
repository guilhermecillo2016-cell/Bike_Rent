"""
servicos_tecnicos/banco_de_dados/repository_estacao.py
-----------------------------------------------------------
Armazenamento em memória das estações cadastradas pelo administrador.

`RepositorioEstacaoMemoria` implementa a interface `RepositorioEstacao`
([A13]). As funções de módulo continuam existindo como fachada da instância
padrão (`padrao`).
"""

from typing import Optional

from dominio.geolocalizacao.geolocalizacao import Geolocalizacao
from servicos_tecnicos.banco_de_dados import memoria
from servicos_tecnicos.banco_de_dados.repositorios import RepositorioEstacao
from dominio.estacao.estacao import Estacao


class RepositorioEstacaoMemoria(memoria.ColecaoPorId, RepositorioEstacao):
    colecao = "estacoes"
    atributo_id = "id_estacao"

    def create(
        self, nome: str, endereco: str, latitude: float, longitude: float,
        capacidade_total: int,
    ) -> Estacao:
        estacao = Estacao(
            memoria.proximo_id("estacoes"), nome, endereco, capacidade_total,
            localizacao=Geolocalizacao(latitude, longitude),
        )
        return self.salvar(estacao)


padrao = RepositorioEstacaoMemoria()


# --- Fachada de módulo (assinaturas de sempre) ---------------------------
def create(nome: str, endereco: str, latitude: float, longitude: float, capacidade_total: int) -> Estacao:
    return padrao.create(nome, endereco, latitude, longitude, capacidade_total)


def list_all() -> list[Estacao]:
    return padrao.list_all()


def get_by_id(estacao_id: int) -> Optional[Estacao]:
    return padrao.get_by_id(estacao_id)


def salvar(estacao: Estacao) -> Estacao:
    return padrao.salvar(estacao)
