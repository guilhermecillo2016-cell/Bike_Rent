"""
dominio/usuario/service.py
----------------------------
Regras de negócio do domínio Usuario: validação de CPF, cadastro,
autenticação, hash de senha, emissão/validação de JWT.

O identificador de login é o e-mail (não um "username" separado),
conforme a história de usuário pede.
"""

import os
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from servicos_tecnicos.banco_de_dados import repository_usuario as repo
from servicos_tecnicos.banco_de_dados.models import UsuarioORM
from servicos_tecnicos.banco_de_dados.enums import PapelUsuario
from dominio.usuario.schemas import (
    AdminCreate,
    OperadorCreate,
    TokenData,
    UsuarioCreate,
    UsuarioPublic,
)

# ------------------------------------------------------------------
# Configurações de segurança
# ------------------------------------------------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "troque-esta-chave-por-uma-bem-secreta")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/webclient/login")
oauth2_scheme_admin = OAuth2PasswordBearer(tokenUrl="/adminweb/login")


# ------------------------------------------------------------------
# Validação de CPF (algoritmo oficial dos dígitos verificadores)
# ------------------------------------------------------------------
def cpf_valido(cpf: str) -> bool:
    digitos = re.sub(r"\D", "", cpf)
    if len(digitos) != 11 or digitos == digitos[0] * 11:
        return False

    for pos in (9, 10):
        soma = sum(int(digitos[i]) * ((pos + 1) - i) for i in range(pos))
        digito_esperado = ((soma * 10) % 11) % 10
        if digito_esperado != int(digitos[pos]):
            return False
    return True


def mask_cpf(cpf: Optional[str]) -> Optional[str]:
    if not cpf:
        return None
    digitos = re.sub(r"\D", "", cpf)
    if len(digitos) != 11:
        return cpf
    return f"***.***.***-{digitos[9:]}"


def to_public(usuario: UsuarioORM) -> UsuarioPublic:
    return UsuarioPublic(
        nome=usuario.nome,
        email=usuario.email,
        cpf=mask_cpf(usuario.cpf),
        telefone=usuario.telefone,
        endereco=usuario.endereco,
        papel=usuario.papel,
    )


# ------------------------------------------------------------------
# Senha
# ------------------------------------------------------------------
def get_password_hash(senha: str) -> str:
    return pwd_context.hash(senha)


def verify_password(senha_texto: str, senha_hash: str) -> bool:
    return pwd_context.verify(senha_texto, senha_hash)


# ------------------------------------------------------------------
# Cadastro (História 1) — ciclista
# ------------------------------------------------------------------
def register_user(dados: UsuarioCreate) -> UsuarioORM:
    if repo.get_by_email(dados.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe uma conta com esse e-mail",
        )

    if not cpf_valido(dados.cpf):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CPF inválido",
        )

    cpf = re.sub(r"\D", "", dados.cpf)
    if repo.get_by_cpf(cpf):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe uma conta com esse CPF",
        )

    return repo.create(
        nome=dados.nome,
        email=dados.email,
        senha_hash=get_password_hash(dados.senha),
        cpf=cpf,
        telefone=dados.telefone,
        endereco=dados.endereco,
        papel=PapelUsuario.CICLISTA,
    )


# ------------------------------------------------------------------
# Cadastro da equipe (administrador e operador de campo) — contas
# separadas do ciclista: sem CPF, telefone ou endereço, só nome,
# e-mail e senha (ver AdminCreate/OperadorCreate).
# ------------------------------------------------------------------
def _cadastrar_equipe(dados: AdminCreate, papel: PapelUsuario) -> UsuarioORM:
    if repo.get_by_email(dados.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe uma conta com esse e-mail",
        )

    return repo.create(
        nome=dados.nome,
        email=dados.email,
        senha_hash=get_password_hash(dados.senha),
        papel=papel,
    )


def register_admin(dados: AdminCreate) -> UsuarioORM:
    return _cadastrar_equipe(dados, PapelUsuario.ADMINISTRADOR)


def register_operador(dados: OperadorCreate) -> UsuarioORM:
    return _cadastrar_equipe(dados, PapelUsuario.OPERADOR_CAMPO)


# ------------------------------------------------------------------
# Autenticação
# ------------------------------------------------------------------
def authenticate_user(email: str, senha: str) -> Optional[UsuarioORM]:
    usuario = repo.get_by_email(email)
    if not usuario or not verify_password(senha, usuario.senha_hash):
        return None
    return usuario


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def _usuario_do_token(token: str) -> UsuarioORM:
    """Valida o JWT e devolve o usuário dono dele. Token inválido, expirado,
    sem 'sub' ou de usuário que não existe mais: sempre 401."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception

    usuario = repo.get_by_email(token_data.email)
    if usuario is None:
        raise credentials_exception
    return usuario


def get_current_user(token: str = Depends(oauth2_scheme)) -> UsuarioORM:
    return _usuario_do_token(token)


_ROTULO_PAPEL = {
    PapelUsuario.CICLISTA: "ciclistas",
    PapelUsuario.OPERADOR_CAMPO: "operadores de campo",
    PapelUsuario.ADMINISTRADOR: "administradores",
}


def requer_papel(*papeis: PapelUsuario):
    """Fabrica uma dependency FastAPI que só deixa passar quem tem um dos
    papéis informados: token inválido -> 401; papel não permitido -> 403.

        Depends(requer_papel(PapelUsuario.ADMINISTRADOR))
        Depends(requer_papel(PapelUsuario.ADMINISTRADOR, PapelUsuario.OPERADOR_CAMPO))

    Os papéis são validados na criação (import), então um papel inexistente
    ou nenhum papel falha na hora de subir o app, não só em uso.
    """
    if not papeis:
        raise ValueError("requer_papel precisa de pelo menos um papel")
    permitidos = tuple(PapelUsuario(p) for p in papeis)
    detalhe = "Acesso restrito a " + " e ".join(_ROTULO_PAPEL[p] for p in permitidos)

    def dependency(token: str = Depends(oauth2_scheme_admin)) -> UsuarioORM:
        usuario = _usuario_do_token(token)
        if usuario.papel not in permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=detalhe,
            )
        return usuario

    return dependency


# Atalho mantido para código que já usa o nome antigo (outras trilhas).
get_current_admin_user = requer_papel(PapelUsuario.ADMINISTRADOR)
