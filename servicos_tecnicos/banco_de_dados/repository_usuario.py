"""
servicos_tecnicos/banco_de_dados/repository_usuario.py
-----------------------------------------------------------
Isola o Domínio de detalhes de armazenamento. Hoje é só um dict em
memória (memoria.py); se um banco real entrar depois, só este
arquivo muda.

`RepositorioUsuarioMemoria` implementa a interface `RepositorioUsuario`
([A13]). As funções de módulo continuam existindo como fachada da instância
padrão (`padrao`). O e-mail é a chave até a [A23] trazer `id_usuario`.
"""

from typing import Optional

from servicos_tecnicos.banco_de_dados import memoria
from servicos_tecnicos.banco_de_dados.repositorios import RepositorioUsuario
from dominio.usuario.usuario import Usuario


class RepositorioUsuarioMemoria(RepositorioUsuario):

    def get_by_email(self, email: str) -> Optional[Usuario]:
        return memoria.usuarios.get(email)

    def get_by_cpf(self, cpf: str) -> Optional[Usuario]:
        """Usuário dono do CPF (só números). Quem não tem CPF nunca casa."""
        if not cpf:
            return None
        return next((u for u in memoria.usuarios.values() if u.cpf == cpf), None)

    def create(self, usuario: Usuario) -> Usuario:
        """Guarda o usuário já montado (o e-mail é a chave)."""
        return self.salvar(usuario)

    def salvar(self, usuario: Usuario) -> Usuario:
        memoria.usuarios[usuario.email] = usuario
        return usuario

    def list_all(self) -> list[Usuario]:
        return list(memoria.usuarios.values())


padrao = RepositorioUsuarioMemoria()


# --- Fachada de módulo (assinaturas de sempre) ---------------------------
def get_by_email(email: str) -> Optional[Usuario]:
    return padrao.get_by_email(email)


def get_by_cpf(cpf: str) -> Optional[Usuario]:
    """Usuário dono do CPF (só números). Quem não tem CPF nunca casa."""
    return padrao.get_by_cpf(cpf)


def create(usuario: Usuario) -> Usuario:
    """Guarda o usuário já montado (o e-mail é a chave)."""
    return padrao.create(usuario)


def list_all() -> list[Usuario]:
    return padrao.list_all()


def salvar(usuario: Usuario) -> Usuario:
    return padrao.salvar(usuario)
