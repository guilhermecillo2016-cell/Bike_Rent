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
from dominio.usuario.schemas import AdminCreate, UsuarioCreate, UsuarioPublic, TokenData

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
        email=usuario.email,
        cpf=mask_cpf(usuario.cpf),
        telefone=usuario.telefone,
        endereco=usuario.endereco,
        is_admin=usuario.is_admin,
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

    return repo.create(
        email=dados.email,
        senha_hash=get_password_hash(dados.senha),
        cpf=re.sub(r"\D", "", dados.cpf),
        telefone=dados.telefone,
        endereco=dados.endereco,
        is_admin=False,
    )


# ------------------------------------------------------------------
# Cadastro de administrador — conta separada do ciclista: sem CPF,
# telefone ou endereço, só e-mail/senha (ver AdminCreate).
# ------------------------------------------------------------------
def register_admin(dados: AdminCreate) -> UsuarioORM:
    if repo.get_by_email(dados.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe uma conta com esse e-mail",
        )

    return repo.create(
        email=dados.email,
        senha_hash=get_password_hash(dados.senha),
        is_admin=True,
    )


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


def get_current_user(token: str = Depends(oauth2_scheme)) -> UsuarioORM:
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


def get_current_admin_user(token: str = Depends(oauth2_scheme_admin)) -> UsuarioORM:
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
    if not usuario.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores",
        )
    return usuario
