"""
servicos_tecnicos/banco_de_dados/enums.py
----------------------------------------------
Enumerações do diagrama de projeto, compartilhadas por domínio,
apresentação e persistência. Todas são StrEnum com valor igual ao nome
do membro, então aparecem como texto ("DISPONIVEL") no JSON da API.
"""

from enum import StrEnum


class PapelUsuario(StrEnum):
    """Perfil de acesso (RBAC) do usuário."""

    CICLISTA = "CICLISTA"
    OPERADOR_CAMPO = "OPERADOR_CAMPO"
    ADMINISTRADOR = "ADMINISTRADOR"


class StatusBicicleta(StrEnum):
    """Situação operacional da bicicleta; só DISPONIVEL pode ser alugada."""

    EM_USO = "EM_USO"
    BLOQUEADA = "BLOQUEADA"
    DISPONIVEL = "DISPONIVEL"
    EM_MANUTENCAO = "EM_MANUTENCAO"


class StatusAvaria(StrEnum):
    """Andamento de um reporte de avaria feito pelo ciclista."""

    PENDENTE = "PENDENTE"
    EM_REPARO = "EM_REPARO"
    RESOLVIDO = "RESOLVIDO"


class TipoPagamento(StrEnum):
    """Meio usado em um pagamento (PIX só entra na iteração 3)."""

    CARTAO_CREDITO = "CARTAO_CREDITO"
    CARTAO_DEBITO = "CARTAO_DEBITO"
    PIX = "PIX"


class StatusPagamento(StrEnum):
    """Situação do pagamento: nasce PENDENTE e sai dela uma única vez, para
    APROVADO, RECUSADO ou CANCELADO (pagamento PIX que venceu sem confirmação)."""

    PENDENTE = "PENDENTE"
    APROVADO = "APROVADO"
    RECUSADO = "RECUSADO"
    CANCELADO = "CANCELADO"


class StatusEstacao(StrEnum):
    """Situação operacional da estação; BLOQUEADA não recebe nem libera bicicletas."""

    OPERACIONAL = "OPERACIONAL"
    BLOQUEADA = "BLOQUEADA"
    EM_MANUTENCAO = "EM_MANUTENCAO"
