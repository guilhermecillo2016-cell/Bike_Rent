"""
apresentacao/adminweb.py
----------------------------
Camada de APRESENTAÇÃO: caixa "AdminWeb" do diagrama — rotas
administrativas.

Cobre a História 2 (Criar Estação). O cadastro de administrador é
separado do cadastro público (WebClient) e exige uma chave secreta
(ADMIN_SECRET), para que ninguém vire admin sozinho.
"""

import os
import secrets
from token import OP
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from fastapi.security import OAuth2PasswordRequestForm

from servicos_tecnicos.banco_de_dados.enums import PapelUsuario, StatusBicicleta, StatusAvaria

from dominio.avaria.schemas import AvariaPublic
from dominio.avaria import service as avaria_service

from dominio.usuario.schemas import AdminCreate, OperadorCreate, UsuarioPublic, Token
from dominio.usuario import service as usuario_service

from dominio.estacao.schemas import EstacaoCreate, EstacaoPublic, StatusEstacaoUpdate
from dominio.estacao import service as estacao_service

from dominio.bicicleta.schemas import BicicletaCreate, BicicletaPublic, StatusBicicletaUpdate
from dominio.bicicleta import service as bicicleta_service

from dominio.auditoria.schemas import EventoAuditoriaPublic
from dominio.auditoria import service as auditoria_service

# Troque por uma variável de ambiente em produção:
#   export ADMIN_SECRET="uma-chave-bem-secreta"
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "troque-esta-chave-admin")

if ADMIN_SECRET == "troque-esta-chave-admin":
    print(
        "[AVISO] ADMIN_SECRET está usando o valor padrão. "
        "Defina a variável de ambiente ADMIN_SECRET antes de usar em produção."
    )

router = APIRouter(prefix="/adminweb", tags=["AdminWeb"])

# Quem entra no painel de gestão: a equipe (nunca o ciclista).
PAPEIS_EQUIPE = (PapelUsuario.ADMINISTRADOR, PapelUsuario.OPERADOR_CAMPO)

# Dependencies de permissão (ver usuario_service.requer_papel).
somente_admin = usuario_service.requer_papel(PapelUsuario.ADMINISTRADOR)
equipe = usuario_service.requer_papel(*PAPEIS_EQUIPE)
somente_operador = usuario_service.requer_papel(PapelUsuario.OPERADOR_CAMPO)


@router.post("/register", response_model=UsuarioPublic, status_code=status.HTTP_201_CREATED)
def register_admin(
    dados: AdminCreate,
    x_admin_secret: str = Header(..., alias="X-Admin-Secret"),
):
    # compare_digest evita vazar a chave por tempo de resposta; em bytes
    # porque ele recusa str com caracteres não-ASCII.
    if not secrets.compare_digest(x_admin_secret.encode(), ADMIN_SECRET.encode()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chave de administrador inválida",
        )
    usuario = usuario_service.register_admin(dados)
    return usuario_service.to_public(usuario)


@router.post("/login", response_model=Token)
def login_admin(form_data: OAuth2PasswordRequestForm = Depends()):
    usuario = usuario_service.authenticate_user(form_data.username, form_data.password)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if usuario.papel not in PAPEIS_EQUIPE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores e operadores de campo",
        )
    access_token = usuario_service.create_access_token(data={"sub": usuario.email})
    return Token(access_token=access_token)


# ------------------------------------------------------------------
# Cadastro de operador de campo — só um administrador logado cria
# a conta; ninguém vira operador sozinho.
# ------------------------------------------------------------------
@router.post("/operadores", response_model=UsuarioPublic, status_code=status.HTTP_201_CREATED)
def cadastrar_operador(dados: OperadorCreate, _admin=Depends(somente_admin)):
    usuario = usuario_service.register_operador(dados)
    return usuario_service.to_public(usuario)


# ------------------------------------------------------------------
# História 2 — Criar Estação
# ------------------------------------------------------------------
@router.post("/estacoes", response_model=EstacaoPublic, status_code=status.HTTP_201_CREATED)
def criar_estacao(
    dados: EstacaoCreate,
    _admin=Depends(somente_admin),
):
    return estacao_service.to_public(estacao_service.criar_estacao(dados))


@router.get("/estacoes", response_model=list[EstacaoPublic])
def listar_estacoes(_usuario=Depends(equipe)):
    return [estacao_service.to_public(e) for e in estacao_service.listar_estacoes()]


# ------------------------------------------------------------------
# Bicicletas — cadastro só do administrador; a equipe (administrador e
# operador) consulta, porque o operador precisa enxergar a frota.
# ------------------------------------------------------------------
@router.post("/bicicletas", response_model=BicicletaPublic, status_code=status.HTTP_201_CREATED)
def cadastrar_bicicleta(dados: BicicletaCreate, _admin=Depends(somente_admin)):
    return bicicleta_service.to_public(bicicleta_service.cadastrar_bicicleta(dados))


@router.get("/bicicletas", response_model=list[BicicletaPublic])
def listar_bicicletas(
    status_bicicleta: Optional[StatusBicicleta] = Query(None, alias="status"),
    estacao_id: Optional[int] = None,
    _usuario=Depends(equipe),
):
    bicicletas = bicicleta_service.listar_bicicletas(status_bicicleta, estacao_id)
    return [bicicleta_service.to_public(b) for b in bicicletas]


# ------------------------------------------------------------------
# Gerenciar frota (UC2) — status manual, com auditoria. Administrador e
# operador alteram; só o administrador consulta o histórico.
# ------------------------------------------------------------------
@router.patch("/bicicletas/{bicicleta_id}/status", response_model=BicicletaPublic)
def alterar_status_bicicleta(
    bicicleta_id: int,
    dados: StatusBicicletaUpdate,
    usuario=Depends(equipe),
):
    bicicleta = bicicleta_service.alterar_status_manual(
        bicicleta_id, dados.status, usuario.email
    )
    return bicicleta_service.to_public(bicicleta)


@router.patch("/estacoes/{estacao_id}/status", response_model=EstacaoPublic)
def alterar_status_estacao(
    estacao_id: int,
    dados: StatusEstacaoUpdate,
    usuario=Depends(equipe),
):
    estacao = estacao_service.alterar_status_manual(estacao_id, dados.status, usuario.email)
    return estacao_service.to_public(estacao)


@router.get("/auditoria", response_model=list[EventoAuditoriaPublic])
def listar_auditoria(_admin=Depends(somente_admin)):
    return [auditoria_service.to_public(e) for e in auditoria_service.listar()]

#Avarias
@router.get(
    "/avarias",
    response_model=list[AvariaPublic]
)
def listar_avarias(
    status_avaria: Optional[StatusAvaria] = Query(None, alias="status"),
    _usuario=Depends(equipe)
):
    return [avaria_service.to_public(a) for a in avaria_service.listar_avarias(status_avaria)]

@router.patch(
    "/avarias/{avaria_id}/resolver",
    response_model=AvariaPublic
)
def resolver_avaria(avaria_id: int, operador=Depends(somente_operador)):
    return avaria_service.to_public(avaria_service.resolver_avaria(avaria_id, operador.email))