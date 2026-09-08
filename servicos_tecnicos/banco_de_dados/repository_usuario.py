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


def get_by_email(email: str) -> Optional[UsuarioORM]:
    return memoria.usuarios.get(email)


def create(
    email: str,
    senha_hash: str,
    cpf: str,
    telefone: str,
    endereco: Optional[str],
    is_admin: bool = False,
) -> UsuarioORM:
    usuario = UsuarioORM(
        email=email,
        senha_hash=senha_hash,
        cpf=cpf,
        telefone=telefone,
        endereco=endereco,
        is_admin=is_admin,
    )
    memoria.usuarios[email] = usuario
    return usuario
