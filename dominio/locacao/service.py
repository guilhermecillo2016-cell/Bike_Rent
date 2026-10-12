"""
dominio/locacao/service.py
----------------------------
Regras de negócio do domínio Locacao: início da corrida (RF-07, RN-01,
RN-06, extensão 4-5a). O domínio depende só da interface da trava.
"""

from fastapi import HTTPException, status as http
from datetime import datetime
from typing import Optional


from dominio import locacao
from dominio.bicicleta import service as bicicleta_service
from dominio.estacao import service as estacao_service

from dominio.pagamento import service as pagamento_service
from dominio.pacote import service as pacote_service

from dominio.locacao.schemas import LocacaoPublic, LocacaoAndamento, LocacaoEncerrada
from dominio.locacao import tarifa

from servicos_tecnicos.banco_de_dados import repository_locacao as repo
from servicos_tecnicos.banco_de_dados.enums import StatusBicicleta, StatusEstacao, StatusPagamento
from servicos_tecnicos.banco_de_dados.models import LocacaoORM
from servicos_tecnicos.iot import ErroTrava, obter_trava


class EstacaoDestinoIndisponivel(Exception):
    """Destino bloqueada, em manutenção ou lotada. Carrega as estações
    autorizadas mais próximas com vaga (extensão 7a)."""

    def __init__(self, motivo: str, sugestoes: list):
        self.motivo = motivo
        self.sugestoes = sugestoes


def to_public(locacao: LocacaoORM) -> LocacaoPublic:
    return LocacaoPublic(
        id=locacao.id,
        bicicleta_id=locacao.bicicleta_id,
        estacao_origem_id=locacao.estacao_origem_id,
        data_hora_inicio=locacao.data_hora_inicio,
        em_andamento=locacao.em_andamento,
    )


def iniciar_locacao(usuario_email: str, qr_code: str) -> LocacaoORM:
    """Inicia a corrida. Só cria a locação DEPOIS da trava confirmar.

    409 corrida já ativa / bicicleta sem estação ou estação inoperante;
    400 sem cartão; 404 QR inexistente; BicicletaIndisponivel se inapta;
    503 se a trava não abriu (nada é alterado).
    """
    if repo.get_ativa_by_usuario(usuario_email) is not None:
        raise HTTPException(
            status_code=http.HTTP_409_CONFLICT,
            detail="Você já tem uma corrida em andamento",
        )

    if not pagamento_service.listar_cartoes(usuario_email):
        raise HTTPException(
            status_code=http.HTTP_400_BAD_REQUEST,
            detail="Cadastre um cartão de crédito para alugar uma bicicleta",
        )

    bicicleta = bicicleta_service.validar_qr(qr_code)  # 404 / BicicletaIndisponivel

    if bicicleta.estacao_id is None:
        raise HTTPException(
            status_code=http.HTTP_409_CONFLICT,
            detail="A bicicleta não está em nenhuma estação",
        )
    estacao = estacao_service.obter_estacao(bicicleta.estacao_id)
    if estacao.status != StatusEstacao.OPERACIONAL:
        raise HTTPException(
            status_code=http.HTTP_409_CONFLICT,
            detail="A estação não está operacional",
        )

    # Extensão 4-5a: timeout ou falha -> cancela, nada muda.
    try:
        liberou = obter_trava().abrir(bicicleta.id)
    except ErroTrava:
        liberou = False
    if not liberou:
        raise HTTPException(
            status_code=http.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Não foi possível destravar a bicicleta. Tente outra bicicleta.",
        )

    # Trava confirmada: agora sim a contagem começa (relógio do servidor).
    locacao = repo.create(usuario_email, bicicleta.id, bicicleta.estacao_id)
    estacao_service.remover_bicicleta(bicicleta.id)  # estacao_id = None
    bicicleta_service.set_status(bicicleta.id, StatusBicicleta.EM_USO)
    return locacao

def obter_locacao_ativa(user_email: str) -> LocacaoORM:
    locacao = repo.get_ativa_by_usuario(user_email)
    if locacao is None:
        raise HTTPException(
            status_code=http.HTTP_404_NOT_FOUND,
            detail="Voce não tem nenhuma corrida em andamento"
        )
    return locacao

def calcular_andamento(locacao: LocacaoORM, agora: Optional[datetime] = None) -> LocacaoAndamento:
    agora = agora or datetime.now()
    segundos = max(0, int((agora - locacao.data_hora_inicio).total_seconds()))
    minutos = tarifa.minutos_iniciados(segundos)

    saldo = pacote_service.saldo_minutos(locacao.usuario_email)
    abatidos = min(minutos, saldo)
    custo = tarifa.calcular_valor(minutos - abatidos)

    estacao = estacao_service.obter_estacao(locacao.estacao_origem_id)

    return LocacaoAndamento(
        locacao_id=locacao.id,
        bicicleta_id=locacao.bicicleta_id,
        estacao_origem_id=estacao.id,
        estacao_origem_nome=estacao.nome,
        data_hora_inicio=locacao.data_hora_inicio,
        duracao_segundos=segundos,
        duracao_minutos=minutos,
        minutos_pacote=abatidos,
        custo_estimado=custo,
    )


def encerrar_locacao(
    usuario_email: str, estacao_destino_id: int, agora: Optional[datetime] = None
) -> LocacaoEncerrada:
    """Encerra a corrida (RF-09, RN-02, RN-05).

    404 sem corrida ativa ou destino inexistente; EstacaoDestinoIndisponivel
    (409 + sugestões) se o destino não recebe; 503 se o travamento não foi
    confirmado (a corrida continua ativa, nada muda).

    Falha na cobrança: DECISÃO — a locação fecha mesmo assim (a bicicleta já
    está travada). O pagamento fica RECUSADO/ausente e `cobranca_pendente`
    é True; a corrida nunca fica aberta por causa de cobrança.
    """
    locacao = obter_locacao_ativa(usuario_email)
    destino = estacao_service.obter_estacao(estacao_destino_id)

    # 1) Destino precisa receber a bicicleta (antes de mexer na trava)
    if destino.status != StatusEstacao.OPERACIONAL:
        raise EstacaoDestinoIndisponivel(
            "A estação de destino não está operacional",
            estacao_service.estacoes_proximas_com_vaga(destino),
        )
    if estacao_service.vagas_disponiveis(destino) <= 0:
        raise EstacaoDestinoIndisponivel(
            "A estação de destino está lotada",
            estacao_service.estacoes_proximas_com_vaga(destino),
        )

    # 2) Travamento físico (RN-02): sem confirmação, a corrida segue
    try:
        travou = obter_trava().confirmar_travamento(locacao.bicicleta_id, destino.id)
    except ErroTrava:
        travou = False
    if not travou:
        raise HTTPException(
            status_code=http.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Travamento não confirmado. Encaixe bem a bicicleta e tente novamente.",
        )

    # 3) Devolve a bicicleta (já validado: não falha)
    estacao_service.alocar_bicicleta(destino.id, locacao.bicicleta_id)
    bicicleta = bicicleta_service.finalizar_uso(locacao.bicicleta_id)  # DISPONIVEL ou EM_MANUTENCAO

    # 4) Tarifa: abate o pacote e cobra só o excedente (RN-04/RN-05)
    fim = agora or datetime.now()
    segundos = max(0, int((fim - locacao.data_hora_inicio).total_seconds()))
    minutos = tarifa.minutos_iniciados(segundos)
    abatidos = pacote_service.abater_minutos(usuario_email, minutos)
    valor = tarifa.calcular_valor(minutos - abatidos)

    # 5) Fecha a locação ANTES de cobrar
    locacao.estacao_destino_id = destino.id
    locacao.data_hora_fim = fim
    locacao.duracao_minutos = minutos
    locacao.minutos_pacote = abatidos
    locacao.valor_total = valor
    locacao.em_andamento = False

    # 6) Cobrança do excedente (extensão 9-10a: valor 0 -> sem cobrança)
    pagamento = None
    if valor > 0:
        try:
            pagamento = pagamento_service.PagamentoService().cobrar_corrida(
                usuario_email, valor, locacao.id
            )
        except HTTPException:
            pagamento = None  # ex.: sem cartão de crédito válido; corrida já está fechada

    pendente = valor > 0 and (pagamento is None or pagamento.status != StatusPagamento.APROVADO)

    return LocacaoEncerrada(
        locacao_id=locacao.id,
        bicicleta_id=locacao.bicicleta_id,
        estacao_origem_id=locacao.estacao_origem_id,
        estacao_destino_id=destino.id,
        data_hora_inicio=locacao.data_hora_inicio,
        data_hora_fim=fim,
        duracao_segundos=segundos,
        duracao_minutos=minutos,
        minutos_pacote=abatidos,
        valor_total=valor,
        pagamento_status=pagamento.status if pagamento else None,
        cobranca_pendente=pendente,
        bicicleta_em_manutencao=bicicleta.status == StatusBicicleta.EM_MANUTENCAO,
    )