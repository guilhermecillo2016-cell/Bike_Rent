"""
apresentacao/webclient.py
----------------------------
Camada de APRESENTAÇÃO: caixa "WebClient" do diagrama — rotas que o
ciclista final consome.

Cobre as Histórias 1 (Cadastrar) e 3 (Vincular Método de Pagamento),
além de login/perfil e uma listagem pública de estações (para o
ciclista ver onde há bicicletas disponíveis).
"""


from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse

from apresentacao.exceptions import _resposta_indisponivel, _resposta_estacao_indisponivel

from servicos_tecnicos.banco_de_dados.enums import PapelUsuario
from servicos_tecnicos.banco_de_dados.models import UsuarioORM

from dominio.bicicleta.schemas import BicicletaPublic, QrValidarRequest
from dominio.bicicleta import service as bicicleta_service

from dominio.usuario.schemas import UsuarioCreate, UsuarioPublic, Token
from dominio.usuario import service as usuario_service

from dominio.pacote.schemas import (
    CompraPacoteRequest,
    ItemCatalogo,
    PacoteCompradoResponse,
    PacoteResponse,
)
from dominio.pacote import service as pacote_service

from dominio.pagamento.schemas import CartaoCreate, CartaoPublic
from dominio.pagamento import service as pagamento_service

from dominio.estacao.schemas import EstacaoPublic
from dominio.estacao import service as estacao_service

from dominio.locacao.schemas import (
    LocacaoCreate,
    LocacaoPublic,
    LocacaoAndamento,
    LocacaoEncerrada,
    EncerrarLocacaoRequest
)
from dominio.locacao import service as locacao_service


router = APIRouter(prefix="/webclient", tags=["WebClient"])


# ------------------------------------------------------------------
# História 1 — Cadastrar
# ------------------------------------------------------------------
@router.post("/register", response_model=UsuarioPublic, status_code=status.HTTP_201_CREATED)
def register(dados: UsuarioCreate):
    usuario = usuario_service.register_user(dados)
    return usuario_service.to_public(usuario)


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # form_data.username carrega o e-mail (é o nome de campo padrão do OAuth2)
    usuario = usuario_service.authenticate_user(form_data.username, form_data.password)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if usuario.papel != PapelUsuario.CICLISTA:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Contas de administrador e de operador devem acessar /gestao.html",
        )
    access_token = usuario_service.create_access_token(data={"sub": usuario.email})
    return Token(access_token=access_token)


@router.get("/me", response_model=UsuarioPublic)
def read_current_user(usuario: UsuarioORM = Depends(usuario_service.get_current_user)):
    return usuario_service.to_public(usuario)


# ------------------------------------------------------------------
# História 3 — Vincular Método de Pagamento (ciclista autenticado)
# ------------------------------------------------------------------
@router.post("/pagamentos", response_model=CartaoPublic, status_code=status.HTTP_201_CREATED)
def vincular_cartao(
    dados: CartaoCreate,
    usuario: UsuarioORM = Depends(usuario_service.get_current_user),
):
    cartao = pagamento_service.vincular_cartao(usuario.email, dados)
    return cartao


@router.get("/pagamentos", response_model=list[CartaoPublic])
def meus_cartoes(usuario: UsuarioORM = Depends(usuario_service.get_current_user)):
    return pagamento_service.listar_cartoes(usuario.email)

@router.delete("/pagamentos/{token}", status_code=status.HTTP_204_NO_CONTENT)
def remover_cartao(
    token: str,
    usuario: UsuarioORM = Depends(usuario_service.get_current_user)
):
    # O serviço deve lançar HTTPException(404) caso o cartão não exista ou não pertença ao usuário
    removido = pagamento_service.remover_cartao(usuario.email, token)
    if not removido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cartão não encontrado ou não pertence a este usuário."
        )

#Validação de QRCode da Bicleta
@router.post(
        "/qr/validar",
        response_model=BicicletaPublic,
        responses={404: {"description" : "QR Code não encontrado"},
                   409: {"description" : "Bicicleta Indisponível"}}
)
def validar_qr(
    dados: QrValidarRequest,
    _usuario: UsuarioORM = Depends(usuario_service.get_current_user)
):
    try:
        bicicleta = bicicleta_service.validar_qr(dados.qr_code)
    except bicicleta_service.BicicletaIndisponivel as e:
        return _resposta_indisponivel(e)
    return bicicleta_service.to_public(bicicleta)

#Inicio da corrida
@router.post("/locacoes", response_model=LocacaoPublic, status_code=status.HTTP_201_CREATED)
def iniciar_locacao(
    dados: LocacaoCreate,
    usuario: UsuarioORM = Depends(usuario_service.get_current_user),
):
    try:
        locacao = locacao_service.iniciar_locacao(usuario.email, dados.qr_code)
    except bicicleta_service.BicicletaIndisponivel as e:
        return _resposta_indisponivel(e)
    return locacao_service.to_public(locacao)

@router.get(
    "/locacoes/ativa",
    response_model=LocacaoAndamento,
    responses={404: {"description": "Sem corrida em andamento"}},
)
def corrida_ativa(usuario: UsuarioORM = Depends(usuario_service.get_current_user)):
    locacao = locacao_service.obter_locacao_ativa(usuario.email)
    return locacao_service.calcular_andamento(locacao)

#Finalizar corrida
@router.post(
    "/locacoes/encerrar",
    response_model=LocacaoEncerrada,
    responses={
        404: {"description": "Sem corrida ativa ou estação inexistente"},
        409: {"description": "Estação de destino lotada/inoperante (com sugestões)"},
        503: {"description": "Travamento não confirmado"},
    },
)
def encerrar_locacao(
    dados: EncerrarLocacaoRequest,
    usuario: UsuarioORM = Depends(usuario_service.get_current_user),
):
    try:
        return locacao_service.encerrar_locacao(usuario.email, dados.estacao_id)
    except locacao_service.EstacaoDestinoIndisponivel as e:
        return _resposta_estacao_indisponivel(e)

# ------------------------------------------------------------------
# Extra: listagem pública de estações (não é uma das 3 histórias,
# mas mostra que a estação criada pelo admin "fica disponível no
# sistema", como o texto da História 2 descreve)
# ------------------------------------------------------------------
@router.get("/estacoes", response_model=list[EstacaoPublic])
def listar_estacoes_publico():
    return [estacao_service.to_public(e) for e in estacao_service.listar_estacoes()]

@router.get("/pacotes/catalogo", response_model=list[ItemCatalogo])
def catalogo_pacotes():
    return pacote_service.listar_catalogo()
 
#Rotas para os pacotes
@router.post(
    "/pacotes",
    response_model=PacoteCompradoResponse,
    status_code=status.HTTP_201_CREATED,
)
def comprar_pacote(
    dados: CompraPacoteRequest,
    usuario: UsuarioORM = Depends(usuario_service.get_current_user),
):
    # Pagamento recusado NÃO é erro HTTP: o pacote volta inativo e sem saldo,
    # com pagamento_status="RECUSADO".
    pacote, pagamento = pacote_service.comprar_pacote(usuario.email, dados.item_id)
    return PacoteCompradoResponse(
        pacote=PacoteResponse.model_validate(pacote),
        pagamento_status=pagamento.status,
    )
 
 
@router.get("/pacotes", response_model=list[PacoteResponse])
def meus_pacotes(usuario: UsuarioORM = Depends(usuario_service.get_current_user)):
    return pacote_service.listar_pacotes(usuario.email)