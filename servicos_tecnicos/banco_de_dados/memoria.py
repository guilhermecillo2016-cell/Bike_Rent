"""
servicos_tecnicos/banco_de_dados/memoria.py
----------------------------------------------
Camada técnica de PERSISTÊNCIA (caixa "BancoDeDados" no diagrama) —
por enquanto SEM banco de dados real e SEM persistência: os dados
ficam só em memória (dicionários Python) e são perdidos a cada
reinício da aplicação.

Quando um banco de verdade entrar, só esse arquivo (e os
repository_*.py que o usam) precisam mudar.
"""

import itertools
from collections import defaultdict

# username/email -> Usuario
usuarios: dict[str, "object"] = {}

# id da estação -> EstacaoORM
estacoes: dict[int, "object"] = {}

# id da bicicleta -> BicicletaORM
bicicletas: dict[int, "object"] = {}

# id do pacote -> PacoteMinutos
pacotes: dict[int, "object"] = {}

# email do usuário -> lista de Cartao
cartoes: dict[str, list] = {}

# id da locação -> Locacao
locacoes: dict[int, "object"] = {}

# id do pagamento -> Pagamento
pagamentos: dict[int, "object"] = {}

# id do reporte -> ReporteAvaria
avarias: dict[int, "object"] = {}

# id do comprovante -> ComprovanteViagem
comprovantes: dict[int, "object"] = {}

# id do evento -> EventoAuditoria
eventos_auditoria: dict[int, "object"] = {}

# Contador de ids inteiros por coleção (1, 2, 3, ...), no lugar da
# sequência/auto-incremento que um banco real faria.
_contadores = defaultdict(lambda: itertools.count(1))


def proximo_id(colecao: str) -> int:
    return next(_contadores[colecao])
