"""
servicos_tecnicos/banco_de_dados/models.py
----------------------------------------------
Representações internas de cada entidade guardada em memória
(equivalente às "tabelas", mas sem SQL nenhum por trás).
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class UsuarioORM:
    email: str
    senha_hash: str
    cpf: str
    telefone: str
    endereco: Optional[str] = None
    is_admin: bool = False


@dataclass
class EstacaoORM:
    id: str
    nome: str
    endereco: str
    latitude: float
    longitude: float
    capacidade_total: int
    vagas_disponiveis: int


@dataclass
class CartaoORM:
    token: str
    ultimos_digitos: str
    bandeira: str
    nome_titular: str
    validade: str
    apelido: Optional[str] = None
