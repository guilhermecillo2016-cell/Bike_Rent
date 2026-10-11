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

# username/email -> UsuarioORM
usuarios: dict[str, "object"] = {}

# id da estação -> EstacaoORM
estacoes: dict[int, "object"] = {}

# id da bicicleta -> BicicletaORM
bicicletas: dict[int, "object"] = {}

# id do pacote -> PacoteMinutosORM
pacotes: dict[int, "object"] = {}

# email do usuário -> lista de CartaoORM
cartoes: dict[str, list] = {}

# id da locação -> LocacaoORM
locacoes: dict[int, "object"] = {}

# id do pagamento -> PagamentoORM
pagamentos: dict[int, "object"] = {}

# id do reporte -> ReporteAvariaORM
avarias: dict[int, "object"] = {}

# id do comprovante -> ComprovanteORM
comprovantes: dict[int, "object"] = {}

# id do evento -> EventoAuditoriaORM
eventos_auditoria: dict[int, "object"] = {}

# Contador de ids inteiros por coleção (1, 2, 3, ...), no lugar da
# sequência/auto-incremento que um banco real faria.
_contadores = defaultdict(lambda: itertools.count(1))


def proximo_id(colecao: str) -> int:
    return next(_contadores[colecao])
