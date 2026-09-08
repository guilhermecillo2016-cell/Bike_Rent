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

from fastapi import APIRouter, Depends, Header, HTTPException, status

from dominio.usuario.schemas import UsuarioCreate, UsuarioPublic
from dominio.usuario import service as usuario_service

from dominio.estacao.schemas import EstacaoCreate, EstacaoPublic
from dominio.estacao import service as estacao_service

# Troque por uma variável de ambiente em produção:
#   export ADMIN_SECRET="uma-chave-bem-secreta"
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "troque-esta-chave-admin")

if ADMIN_SECRET == "troque-esta-chave-admin":
    print(
        "[AVISO] ADMIN_SECRET está usando o valor padrão. "
        "Defina a variável de ambiente ADMIN_SECRET antes de usar em produção."
    )

router = APIRouter(prefix="/adminweb", tags=["AdminWeb"])


@router.post("/register", response_model=UsuarioPublic, status_code=status.HTTP_201_CREATED)
def register_admin(
    dados: UsuarioCreate,
    x_admin_secret: str = Header(..., alias="X-Admin-Secret"),
):
    if x_admin_secret != ADMIN_SECRET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chave de administrador inválida",
        )
    usuario = usuario_service.register_user(dados, is_admin=True)
    return usuario_service.to_public(usuario)


# ------------------------------------------------------------------
# História 2 — Criar Estação
# ------------------------------------------------------------------
@router.post("/estacoes", response_model=EstacaoPublic, status_code=status.HTTP_201_CREATED)
def criar_estacao(
    dados: EstacaoCreate,
    _admin=Depends(usuario_service.get_current_admin_user),
):
    return estacao_service.criar_estacao(dados)


@router.get("/estacoes", response_model=list[EstacaoPublic])
def listar_estacoes(_admin=Depends(usuario_service.get_current_admin_user)):
    return estacao_service.listar_estacoes()
