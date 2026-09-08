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

# username/email -> UsuarioORM
usuarios: dict[str, "object"] = {}

# id da estação -> EstacaoORM
estacoes: dict[str, "object"] = {}

# email do usuário -> lista de CartaoORM
cartoes: dict[str, list] = {}
