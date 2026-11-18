"""
servicos_tecnicos/banco_de_dados/repository_usuario.py
-----------------------------------------------------------
Isola o Domínio de detalhes de armazenamento. Hoje é só um dict em
memória (memoria.py); se um banco real entrar depois, só este
arquivo muda.
"""

from typing import Optional

from servicos_tecnicos.banco_de_dados import memoria
from dominio.usuario.usuario import Usuario


def get_by_email(email: str) -> Optional[Usuario]:
    return memoria.usuarios.get(email)


def get_by_cpf(cpf: str) -> Optional[Usuario]:
    """Usuário dono do CPF (só números). Quem não tem CPF nunca casa."""
    if not cpf:
        return None
    return next((u for u in memoria.usuarios.values() if u.cpf == cpf), None)


def create(usuario: Usuario) -> Usuario:
    """Guarda o usuário já montado (o e-mail é a chave)."""
    memoria.usuarios[usuario.email] = usuario
    return usuario
