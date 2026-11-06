"""
servicos_tecnicos/seguranca.py
--------------------------------
Hash e conferência de senha (bcrypt). Fica fora do domínio de usuário para
que a própria entidade Usuario consiga se autenticar sem importar o service.
"""

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def gerar_hash(senha: str) -> str:
    return pwd_context.hash(senha)


def conferir_senha(senha_texto: str, senha_hash: str) -> bool:
    return pwd_context.verify(senha_texto, senha_hash)
