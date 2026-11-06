"""
servicos_tecnicos/banco_de_dados/repository_locacao.py
-----------------------------------------------------------
Armazenamento em memória das locações (corridas). Regras como "uma
corrida ativa por ciclista" ficam no service; aqui só se guarda.
"""

from datetime import datetime
from typing import Optional

from dominio.bicicleta.bicicleta import Bicicleta
from dominio.estacao.estacao import Estacao
from dominio.usuario.usuario import Usuario
from servicos_tecnicos.banco_de_dados import memoria
from dominio.locacao.locacao import Locacao


def create(
    usuario: Usuario,
    bicicleta: Bicicleta,
    estacao_origem: Estacao,
) -> Locacao:
    locacao = Locacao(
        usuario, bicicleta, estacao_origem,
        id_locacao=memoria.proximo_id("locacoes"),
    )
    memoria.locacoes[locacao.id_locacao] = locacao
    return locacao


def get_by_id(locacao_id: int) -> Optional[Locacao]:
    return memoria.locacoes.get(locacao_id)


def list_all() -> list[Locacao]:
    return list(memoria.locacoes.values())

def get_ativa_by_usuario(usuario_email: str) -> Optional[Locacao]:
    return next(
        (l for l in memoria.locacoes.values() 
         if l.usuario_email == usuario_email and l.em_andamento),
         None
    )