"""Consulta de estações para o ciclista (RF-04, RF-05, RN-03).

- Lista com bicicletas disponíveis, vagas livres, endereço e status; com
  lat/lng, ordena por distância.
- Estações próximas COM VAGA (extensão 7a do UC1, consumida pela [B5]).
- Estação BLOQUEADA não recebe nem libera bicicletas: não é opção de retirada
  nem de devolução. Na lista geral ela aparece com o status e 0/0; nas próximas
  com vaga ela é excluída.

Estações e contagem de bicicletas podem ser injetadas (testes). Os padrões
dependem dos ORMs do projeto e estão isolados em `_estacoes` e
`_bicicletas_disponiveis`.
"""

from fastapi import HTTPException, status

from dominio.estacao.schemas_disponibilidade import EstacaoDisponibilidade
from dominio.geolocalizacao.geolocalizacao import Geolocalizacao
from servicos_tecnicos import mapas
from servicos_tecnicos.banco_de_dados import memoria
from servicos_tecnicos.banco_de_dados.enums import StatusBicicleta, StatusEstacao


def _estacoes():
    # SUPOSIÇÃO: estacao_service.listar_estacoes() devolve as EstacaoORM.
    from dominio.estacao import service as estacao_service

    return estacao_service.listar_estacoes()


def _bicicletas_disponiveis(estacao) -> int:
    # SUPOSIÇÃO: memoria.bicicletas = {id: BicicletaORM} com `estacao_id` e `status`.
    return estacao.bicicletas_disponiveis  # já conta só as aptas para locação

def _posicao(lat, lng, obrigatoria=False):
    if lat is None and lng is None:
        if obrigatoria:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Informe lat e lng",
            )
        return None
    if lat is None or lng is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe lat e lng juntos",
        )
    try:
        return Geolocalizacao(lat, lng)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


def _item(estacao, contar_bicicletas, distancia=None) -> EstacaoDisponibilidade:
    bloqueada = estacao.status == StatusEstacao.BLOQUEADA
    return EstacaoDisponibilidade(
        id=estacao.id,
        nome=estacao.nome,
        endereco=estacao.endereco,
        status=estacao.status,
        bicicletas_disponiveis=0 if bloqueada else contar_bicicletas(estacao),
        vagas_livres=0 if bloqueada else estacao.vagas_disponiveis,
        distancia_metros=None if distancia is None else round(distancia, 1),
    )


def listar_estacoes(lat=None, lng=None, *, estacoes=None, contar_bicicletas=None):
    """Todas as estações; com lat e lng, ordenadas da mais próxima à mais distante."""
    posicao = _posicao(lat, lng)
    contar = contar_bicicletas or _bicicletas_disponiveis
    lista = list(estacoes if estacoes is not None else _estacoes())

    if posicao is None:
        return [_item(e, contar) for e in lista]
    pares = mapas.estacoes_mais_proximas(
        posicao.latitude, posicao.longitude, len(lista), estacoes=lista
    )
    return [_item(e, contar, dist) for e, dist in pares]


def proximas_com_vaga(lat, lng, n=3, *, estacoes=None, contar_bicicletas=None):
    """As `n` estações mais próximas que podem receber uma bicicleta agora."""
    posicao = _posicao(lat, lng, obrigatoria=True)
    contar = contar_bicicletas or _bicicletas_disponiveis
    candidatas = [
        e
        for e in (estacoes if estacoes is not None else _estacoes())
        if e.status != StatusEstacao.BLOQUEADA and e.vagas_disponiveis > 0
    ]
    pares = mapas.estacoes_mais_proximas(
        posicao.latitude, posicao.longitude, n, estacoes=candidatas
    )
    return [_item(e, contar, dist) for e, dist in pares]