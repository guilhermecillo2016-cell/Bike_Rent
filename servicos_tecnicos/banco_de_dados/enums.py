from enum import StrEnum

class PapelUsuario(StrEnum):
    CICLISTA = "CICLISTA"
    OPERADOR_CAMPO = "OPERADOR_CAMPO"
    ADMINISTRADOR = "ADMINISTRADOR"

class StatusBicicleta(StrEnum):
    EM_USO = "EM_USO"
    BLOQUEADA = "BLOQUEADA"
    DISPONIVEL = "DISPONIVEL"
    EM_MANUTENCAO = "EM_MANUTENCAO"

class StatusAvaria(StrEnum):
    PENDENTE = "PENDENTE"
    EM_REPARO = "EM_REPARO"
    RESOLVIDO = "RESOLVIDO"

class TipoPagamento(StrEnum):
    CARTAO_CREDITO = "CARTAO_CREDITO"
    CARTAO_DEBITO = "CARTAO_DEBITO"
    PIX = "PIX"

class StatusPagamento(StrEnum):
    PENDENTE = "PENDENTE"
    APROVADO = "APROVADO"
    RECUSADO = "RECUSADO"

class StatusEstacao(StrEnum):
    OPERACIONAL = "OPERACIONAL"
    BLOQUEADA = "BLOQUEADA"
    EM_MANUTENCAO = "EM_MANUTENCAO"