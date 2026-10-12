"""
dominio/relatorio/service.py
------------------------------
Relatório analítico (UC3, RF-17, RN-11): receita, ociosidade da frota,
índice de quebras e horário de pico por estação. Tudo calculado sobre os
repositórios, sem guardar nada.

Regras de filtro:
- período: datas inclusivas (inicio 00:00 até fim 23:59); sem data = sem limite.
- estação: corrida conta na estação onde começou; pacote não pertence a
  nenhuma estação (some do filtro); avaria conta pela estação atual da
  bicicleta; na ociosidade, a frota é a das bicicletas que estão hoje na
  estação.
"""

from collections import Counter
from datetime import date, datetime
from typing import Optional

from fastapi import HTTPException, status as http

from dominio.estacao import service as estacao_service
from dominio.relatorio.schemas import HorarioPico, RelatorioAnalitico
from servicos_tecnicos.banco_de_dados import repository_avaria
from servicos_tecnicos.banco_de_dados import repository_bicicleta
from servicos_tecnicos.banco_de_dados import repository_locacao
from servicos_tecnicos.banco_de_dados import repository_pagamento
from servicos_tecnicos.banco_de_dados.enums import StatusPagamento


def _no_periodo(momento: datetime, inicio: Optional[date], fim: Optional[date]) -> bool:
    if inicio is not None and momento.date() < inicio:
        return False
    if fim is not None and momento.date() > fim:
        return False
    return True


def _receita(pagamentos, locacoes_da_estacao: Optional[set[int]]):
    """(corridas, pacotes) dos pagamentos aprovados já filtrados por período.
    Com filtro de estação, só entram as corridas dela."""
    corridas = pacotes = 0.0
    for p in pagamentos:
        if p.locacao_id is not None:
            if locacoes_da_estacao is None or p.locacao_id in locacoes_da_estacao:
                corridas += p.valor
        elif p.pacote_id is not None and locacoes_da_estacao is None:
            pacotes += p.valor
    return round(corridas, 2), round(pacotes, 2)


def _ociosidade(universo, locacoes_periodo):
    """Fração da frota sem nenhuma corrida iniciada no período."""
    usadas = {l.bicicleta_id for l in locacoes_periodo}
    ociosas = [b for b in universo if b.id not in usadas]
    taxa = len(ociosas) / len(universo) if universo else 0.0
    return len(universo), len(ociosas), round(taxa, 4)


def _horarios_pico(locacoes) -> list[HorarioPico]:
    por_estacao: dict[int, Counter] = {}
    for l in locacoes:
        por_estacao.setdefault(l.estacao_origem_id, Counter())[l.data_hora_inicio.hour] += 1

    picos = []
    for estacao_id in sorted(por_estacao):
        horas = por_estacao[estacao_id]
        mais_cheia = max(horas.values())
        hora = min(h for h, n in horas.items() if n == mais_cheia)  # empate: a mais cedo
        picos.append(
            HorarioPico(
                estacao_id=estacao_id,
                estacao_nome=estacao_service.obter_estacao(estacao_id).nome,
                total_locacoes=sum(horas.values()),
                hora_pico=hora,
                locacoes_na_hora_pico=mais_cheia,
            )
        )
    return picos


def _estacao_da_bicicleta(bicicleta_id: int) -> Optional[int]:
    bicicleta = repository_bicicleta.get_by_id(bicicleta_id)
    return bicicleta.estacao_id if bicicleta else None


def gerar_relatorio(
    inicio: Optional[date] = None,
    fim: Optional[date] = None,
    estacao_id: Optional[int] = None,
) -> RelatorioAnalitico:
    """400 se o início é depois do fim; 404 se a estação não existe."""
    if inicio is not None and fim is not None and inicio > fim:
        raise HTTPException(
            status_code=http.HTTP_400_BAD_REQUEST,
            detail="O início do período não pode ser depois do fim",
        )
    if estacao_id is not None:
        estacao_service.obter_estacao(estacao_id)

    todas = repository_locacao.list_all()
    locacoes_periodo = [l for l in todas if _no_periodo(l.data_hora_inicio, inicio, fim)]
    locacoes = [
        l for l in locacoes_periodo
        if estacao_id is None or l.estacao_origem_id == estacao_id
    ]

    pagamentos = [
        p for p in repository_pagamento.list_all()
        if p.status == StatusPagamento.APROVADO and _no_periodo(p.data_hora, inicio, fim)
    ]
    da_estacao = None
    if estacao_id is not None:
        da_estacao = {l.id for l in todas if l.estacao_origem_id == estacao_id}
    corridas, pacotes = _receita(pagamentos, da_estacao)

    bicicletas = repository_bicicleta.list_all()
    if estacao_id is not None:
        bicicletas = [b for b in bicicletas if b.estacao_id == estacao_id]
    total_bicicletas, ociosas, taxa = _ociosidade(bicicletas, locacoes_periodo)

    avarias = [
        a for a in repository_avaria.list_all()
        if _no_periodo(a.data_hora, inicio, fim)
        and (estacao_id is None or _estacao_da_bicicleta(a.bicicleta_id) == estacao_id)
    ]
    indice = round(len(avarias) / len(locacoes), 4) if locacoes else 0.0

    return RelatorioAnalitico(
        data_geracao=datetime.now(),
        inicio=inicio,
        fim=fim,
        estacao_id=estacao_id,
        receita_total=round(corridas + pacotes, 2),
        receita_corridas=corridas,
        receita_pacotes=pacotes,
        total_locacoes=len(locacoes),
        bicicletas_total=total_bicicletas,
        bicicletas_ociosas=ociosas,
        taxa_ociosidade=taxa,
        total_avarias=len(avarias),
        indice_quebras=indice,
        horarios_pico=_horarios_pico(locacoes),
    )
