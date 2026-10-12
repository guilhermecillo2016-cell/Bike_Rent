"""Gateway de pagamento SIMULADO (RF-12).

Não faz chamada de rede. Corrida e compra de pacote usam o mesmo gateway.

Para testar o fluxo de recusa, use o cartão de teste cujo token é
`TOKEN_CARTAO_RECUSADO`: toda cobrança nele é RECUSADA. Qualquer outro token
válido é APROVADO.
"""

from servicos_tecnicos.banco_de_dados.enums import StatusPagamento

TOKEN_CARTAO_RECUSADO = "tok_test_recusado"


def cobrar(token: str, valor: float) -> StatusPagamento:
    """Simula a cobrança de `valor` no cartão identificado por `token`.

    Devolve APROVADO ou RECUSADO; nunca levanta exceção por recusa.
    """
    if not token or token == TOKEN_CARTAO_RECUSADO:
        return StatusPagamento.RECUSADO
    return StatusPagamento.APROVADO