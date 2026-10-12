"""Tarifa da locação (RN-04, parte "minuto fracionado").

A tarifa não é uma entidade: é uma regra de cálculo da própria locação
(comentário da professora, item 6).

Regras
------
- valor = VALOR_BASE + minutos_a_cobrar * VALOR_POR_MINUTO
- Arredondamento: minuto iniciado conta como minuto cheio (teto). A conversão
  de segundos para minutos é feita por `minutos_iniciados`, antes de chamar
  `calcular_valor`; esta recebe um número inteiro de minutos já arredondado.
- Recebe só os minutos a cobrar (excedente depois de abater o pacote, ver
  [C8] e [B5]). Não conhece pacote.
- Se não há nada a cobrar (0 minutos, ex.: pacote cobriu a corrida inteira),
  o valor é 0.0 e o valor base NÃO é cobrado.
- O resultado é arredondado em 2 casas decimais.

Configuração (variáveis de ambiente, com valores padrão provisórios):
    TARIFA_VALOR_BASE        (padrão 3.00)
    TARIFA_VALOR_POR_MINUTO  (padrão 0.50)
"""

import os

VALOR_BASE: float = float(os.getenv("TARIFA_VALOR_BASE", "3.00"))
VALOR_POR_MINUTO: float = float(os.getenv("TARIFA_VALOR_POR_MINUTO", "0.50"))


def minutos_iniciados(duracao_segundos: int) -> int:
    """Converte segundos em minutos; minuto iniciado conta como cheio.

    0 s -> 0 min; 1 s -> 1 min; 60 s -> 1 min; 61 s -> 2 min.
    """
    if duracao_segundos < 0:
        raise ValueError("duracao_segundos não pode ser negativa")
    return -(-duracao_segundos // 60)  # teto em aritmética inteira


def calcular_valor(duracao_min: int) -> float:
    """Valor a cobrar por `duracao_min` minutos (já arredondados e já
    descontado o pacote). Função pura."""
    if duracao_min < 0:
        raise ValueError("duracao_min não pode ser negativa")
    if duracao_min == 0:
        return 0.0
    return round(VALOR_BASE + duracao_min * VALOR_POR_MINUTO, 2)