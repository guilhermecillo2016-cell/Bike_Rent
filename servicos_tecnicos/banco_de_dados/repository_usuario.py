"""
servicos_tecnicos/banco_de_dados/repository_usuario.py
-----------------------------------------------------------
Isola o Domínio de detalhes de armazenamento. Hoje é só um dict em
memória (memoria.py); se um banco real entrar depois, só este
arquivo muda.
"""

from typing import Optional

from servicos_tecnicos.banco_de_dados import memoria
from servicos_tecnicos.banco_de_dados.models import UsuarioORM
from servicos_tecnicos.banco_de_dados.enums import PapelUsuario


def get_by_email(email: str) -> Optional[UsuarioORM]:
    return memoria.usuarios.get(email)


def create(
    nome: str,
    email: str,
    senha_hash: str,
    papel: PapelUsuario,
    cpf: Optional[str] = None,
    telefone: Optional[str] = None,
    endereco: Optional[str] = None,
) -> UsuarioORM:
    usuario = UsuarioORM(
        nome=nome,
        email=email,
        senha_hash=senha_hash,
        cpf=cpf,
        papel=papel,
        telefone=telefone,
        endereco=endereco,
    )
    memoria.usuarios[email] = usuario
    return usuario
