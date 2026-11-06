"""Tarifa da locação (RN-04, parte "minuto fracionado").

A tarifa não é uma entidade: é uma regra de cálculo da própria locação
(comentário da professora, item 6). Por isso a regra mora na classe
`Locacao` (`minutos_iniciados`, `valor_por_minutos`,
`calcular_valor_trajeto`); este módulo só mantém os nomes antigos
apontando para ela.

Regras
------
- valor = VALOR_BASE + minutos_a_cobrar * VALOR_POR_MINUTO
- Arredondamento: minuto iniciado conta como minuto cheio (teto).
- Recebe só os minutos a cobrar (excedente depois de abater o pacote).
- Se não há nada a cobrar (0 minutos), o valor é 0.0 e o valor base NÃO
  é cobrado.
- O resultado é arredondado em 2 casas decimais.

Configuração (variáveis de ambiente, com valores padrão provisórios):
    TARIFA_VALOR_BASE        (padrão 3.00)
    TARIFA_VALOR_POR_MINUTO  (padrão 0.50)
"""

from dominio.locacao.locacao import Locacao

VALOR_BASE: float = Locacao.VALOR_BASE
VALOR_POR_MINUTO: float = Locacao.VALOR_POR_MINUTO


def minutos_iniciados(duracao_segundos: int) -> int:
    return Locacao.minutos_iniciados(duracao_segundos)


def calcular_valor(duracao_min: int) -> float:
    return Locacao.valor_por_minutos(duracao_min)
