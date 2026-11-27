"""
servicos_tecnicos/banco_de_dados/repository_locacao.py
-----------------------------------------------------------
Armazenamento em memória das locações (corridas). Regras como "uma
corrida ativa por ciclista" ficam no service; aqui só se guarda.

`RepositorioLocacaoMemoria` implementa a interface `RepositorioLocacao`
([A13]). As funções de módulo continuam existindo como fachada da instância
padrão (`padrao`).
"""

from typing import Optional

from dominio.bicicleta.bicicleta import Bicicleta
from dominio.estacao.estacao import Estacao
from dominio.usuario.usuario import Usuario
from servicos_tecnicos.banco_de_dados import memoria
from servicos_tecnicos.banco_de_dados.repositorios import RepositorioLocacao
from dominio.locacao.locacao import Locacao


class RepositorioLocacaoMemoria(memoria.ColecaoPorId, RepositorioLocacao):
    colecao = "locacoes"
    atributo_id = "id_locacao"

    def create(self, usuario: Usuario, bicicleta: Bicicleta, estacao_origem: Estacao) -> Locacao:
        locacao = Locacao(
            usuario, bicicleta, estacao_origem,
            id_locacao=memoria.proximo_id("locacoes"),
        )
        return self.salvar(locacao)

    def get_ativa_by_usuario(self, usuario_email: str) -> Optional[Locacao]:
        return next(
            (l for l in self.list_all()
             if l.usuario_email == usuario_email and l.em_andamento),
            None,
        )


padrao = RepositorioLocacaoMemoria()


# --- Fachada de módulo (assinaturas de sempre) ---------------------------
def create(
    usuario: Usuario,
    bicicleta: Bicicleta,
    estacao_origem: Estacao,
) -> Locacao:
    return padrao.create(usuario, bicicleta, estacao_origem)


def get_by_id(locacao_id: int) -> Optional[Locacao]:
    return padrao.get_by_id(locacao_id)


def list_all() -> list[Locacao]:
    return padrao.list_all()


def get_ativa_by_usuario(usuario_email: str) -> Optional[Locacao]:
    return padrao.get_ativa_by_usuario(usuario_email)


def salvar(locacao: Locacao) -> Locacao:
    return padrao.salvar(locacao)
