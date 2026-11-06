"""
dominio/estacao/service.py
----------------------------
Regras de negócio do domínio Estacao: cadastro (feito por um
administrador) e listagem das estações disponíveis no sistema.

A validação de faixa de latitude/longitude e de capacidade > 0 já
acontece no schema (EstacaoCreate); aqui ficam regras adicionais de
negócio.
"""
from fastapi import HTTPException, status as http

from dominio.auditoria import service as auditoria_service
from servicos_tecnicos.banco_de_dados import repository_bicicleta
from servicos_tecnicos.banco_de_dados import repository_estacao as repo
from servicos_tecnicos.banco_de_dados.enums import StatusEstacao
from servicos_tecnicos.banco_de_dados.models import BicicletaORM
from dominio.estacao.estacao import Estacao
from dominio.estacao.schemas import EstacaoCreate, EstacaoPublic


def vagas_disponiveis(estacao: Estacao) -> int:
    """Vagas livres = capacidade - bicicletas que estão na estação."""
    return estacao.vagas_disponiveis


def bicicletas_disponiveis(estacao: Estacao) -> int:
    return estacao.quantidade_bicicletas_disponiveis()


def to_public(estacao: Estacao) -> EstacaoPublic:
    return EstacaoPublic(
        id=estacao.id,
        nome=estacao.nome,
        endereco=estacao.endereco,
        latitude=estacao.latitude,
        longitude=estacao.longitude,
        capacidade_total=estacao.capacidade_total,
        vagas_disponiveis=vagas_disponiveis(estacao),
        bicicletas_disponiveis=bicicletas_disponiveis(estacao),
        status=estacao.status,
    )


def obter_estacao(estacao_id: int) -> Estacao:
    """Devolve a estação ou levanta 404."""
    estacao = repo.get_by_id(estacao_id)
    if estacao is None:
        raise HTTPException(
            status_code=http.HTTP_404_NOT_FOUND,
            detail="Estação não encontrada",
        )
    return estacao


def exigir_vaga_livre(estacao_id: int) -> Estacao:
    """Garante que a estação pode receber uma bicicleta agora.

    404 se não existe; 409 se não está OPERACIONAL (bloqueada ou em
    manutenção não recebe nem libera bicicletas) ou se está lotada.
    Devolve a estação.
    """
    estacao = obter_estacao(estacao_id)
    estacao.exigir_vaga_livre()
    return estacao


def possui_vaga_livre(estacao_id: int) -> bool:
    """Versão sim/não de exigir_vaga_livre (404 se a estação não existe)."""
    return obter_estacao(estacao_id).possui_vaga_livre()


def alocar_bicicleta(estacao_id: int, bicicleta_id: int) -> BicicletaORM:
    """Estaciona a bicicleta na estação. 404 se algum dos dois não existe;
    409 se a estação não aceita ou se a bicicleta já está em outra."""
    estacao = exigir_vaga_livre(estacao_id)

    bicicleta = repository_bicicleta.get_by_id(bicicleta_id)
    if bicicleta is None:
        raise HTTPException(
            status_code=http.HTTP_404_NOT_FOUND,
            detail="Bicicleta não encontrada",
        )

    estacao.alocar_bicicleta(bicicleta)
    return bicicleta


def remover_bicicleta(bicicleta_id: int) -> BicicletaORM:
    """Tira a bicicleta da estação. 404 se ela não existe; 409 se não está em
    nenhuma estação ou se a estação dela não está operacional."""
    bicicleta = repository_bicicleta.get_by_id(bicicleta_id)
    if bicicleta is None:
        raise HTTPException(
            status_code=http.HTTP_404_NOT_FOUND,
            detail="Bicicleta não encontrada",
        )
    if bicicleta.estacao is None:
        raise HTTPException(
            status_code=http.HTTP_409_CONFLICT,
            detail="A bicicleta não está em nenhuma estação",
        )

    bicicleta.estacao.remover_bicicleta(bicicleta)
    return bicicleta


def alterar_status_manual(
    estacao_id: int, novo_status: StatusEstacao, usuario_email: str
) -> Estacao:
    """Troca o status da estação à mão e registra na auditoria. 404 se não existe."""
    estacao = obter_estacao(estacao_id)
    novo_status = StatusEstacao(novo_status)
    if novo_status == estacao.status:
        return estacao

    anterior = str(estacao.status)
    estacao.set_status(novo_status)
    auditoria_service.registrar(
        usuario_email, "ESTACAO", estacao.id, anterior, str(novo_status)
    )
    return estacao


def criar_estacao(dados: EstacaoCreate) -> Estacao:
    return repo.create(
        nome=dados.nome,
        endereco=dados.endereco,
        latitude=dados.latitude,
        longitude=dados.longitude,
        capacidade_total=dados.capacidade_total,
    )


def listar_estacoes() -> list[Estacao]:
    return repo.list_all()


def estacoes_proximas_com_vaga(referencia: Estacao, limite: int = 3) -> list[Estacao]:
    """Estações OPERACIONAIS com vaga livre, da mais perto para a mais longe."""
    candidatas = [
        e for e in repo.list_all()
        if e.id != referencia.id
        and e.status == StatusEstacao.OPERACIONAL
        and vagas_disponiveis(e) > 0
    ]
    candidatas.sort(key=referencia.distancia_ate_em_metros)
    return candidatas[:limite]