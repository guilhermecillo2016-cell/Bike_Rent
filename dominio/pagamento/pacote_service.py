"""
dominio/pagamento/pacote_service.py
-------------------------------------
Consulta de saldo de pacotes de minutos. Versão mínima só de leitura,
para a [B4]; a [C8] completa (compra/ativação/débito) estende este arquivo.
"""

from datetime import datetime
from typing import Optional

from servicos_tecnicos.banco_de_dados import repository_pacote

#TODO: ARRUMAR NA ISSUE C8
def saldo_minutos(usuario_email: str, agora: Optional[datetime] = None) -> int:
    """Soma dos minutos restantes dos pacotes ATIVOS e dentro da validade."""
    agora = agora or datetime.now()
    return sum(
        p.minutos_restantes
        for p in repository_pacote.list_by_usuario(usuario_email)
        if p.ativo and p.data_validade > agora
    )