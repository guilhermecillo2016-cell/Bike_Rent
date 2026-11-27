"""
dominio/comprovante/service.py
--------------------------------
Comprovante digital da viagem (RF-13, RN-08). Nunca expõe número
completo de cartão (RNF-09): só bandeira e últimos dígitos.
"""

from fastapi import HTTPException, status as http

from dominio.comprovante.schemas import ComprovantePublic
from servicos_tecnicos.banco_de_dados.fabrica import repositorios
from dominio.locacao.locacao import Locacao
from dominio.comprovante.comprovante_viagem import ComprovanteViagem


def emitir(locacao: Locacao, pagamento=None) -> ComprovanteViagem:
    """Gera o comprovante ao encerrar. `pagamento` é None quando não houve
    cobrança (pacote cobriu tudo) ou quando ela não pôde ser feita."""
    return repositorios().comprovante.create(locacao, pagamento)


def _descrever_cartao(email: str, token) -> str:
    for c in repositorios().cartao.list_cartoes(email):
        if c.token == token:
            tipo = "crédito" if c.tipo in ("credito", "CARTAO_CREDITO") else "débito"
            return f"{c.bandeira} {tipo} final {c.ultimos_digitos}"
    return "Cartão"


def _metodo(locacao: Locacao, pagamento) -> str:
    if (locacao.valor_total or 0) == 0:
        return "Pago com pacote de minutos"
    if pagamento is None:
        return "Cobrança pendente"
    cartao = _descrever_cartao(locacao.usuario_email, pagamento.token_cartao)
    return f"Pacote de minutos + {cartao}" if locacao.minutos_pacote else cartao


def to_public(c: ComprovanteViagem, locacao: Locacao) -> ComprovantePublic:
    pagamento = c.pagamento if c.pagamento_id else None
    return ComprovantePublic(
        id=c.id,
        locacao_id=locacao.id,
        data_emissao=c.data_emissao,
        trajeto=c.resumo_trajeto,
        data_hora_inicio=locacao.data_hora_inicio,
        data_hora_fim=locacao.data_hora_fim,
        duracao_minutos=locacao.duracao_minutos or 0,
        minutos_pacote=locacao.minutos_pacote,
        tarifa_aplicada=c.tarifa_aplicada,
        metodo_pagamento=_metodo(locacao, pagamento),
        pago_com_pacote=(locacao.valor_total or 0) == 0,
        pagamento_status=pagamento.status if pagamento else None,
    )


def obter_do_ciclista(locacao_id: int, usuario_email: str) -> ComprovantePublic:
    """404 se a locação não existe, é de outro ciclista ou ainda não tem
    comprovante (mesma mensagem nos três casos, para não vazar existência)."""
    nao_encontrado = HTTPException(
        status_code=http.HTTP_404_NOT_FOUND, detail="Comprovante não encontrado"
    )
    locacao = repositorios().locacao.get_by_id(locacao_id)
    if locacao is None or locacao.usuario_email != usuario_email:
        raise nao_encontrado
    comprovante = repositorios().comprovante.get_by_locacao(locacao_id)
    if comprovante is None:
        raise nao_encontrado
    return to_public(comprovante, locacao)