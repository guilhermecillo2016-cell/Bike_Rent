"""
servicos_tecnicos/banco_de_dados/models.py
----------------------------------------------
Representações internas de cada entidade guardada em memória
(equivalente às "tabelas", mas sem SQL nenhum por trás).

Convenções: a chave de cada entidade é `id` (int, gerado por
memoria.proximo_id); referências a outras entidades são campos
`<entidade>_id`. O usuário é a exceção: é identificado pelo e-mail,
então a referência a ele é `usuario_email`.
"""

from dataclasses import dataclass
from typing import Literal, Optional
from datetime import datetime
from servicos_tecnicos.banco_de_dados.enums import (
    PapelUsuario,
    StatusAvaria,
    StatusBicicleta,
    StatusEstacao,
    StatusPagamento,
    TipoPagamento,
)


@dataclass
class UsuarioORM:
    nome: str
    email: str
    senha_hash: str
    papel: PapelUsuario
    # cpf/telefone só existem para ciclistas; administrador não os possui
    cpf: Optional[str] = None
    telefone: Optional[str] = None
    endereco: Optional[str] = None


@dataclass
class EstacaoORM:
    id: int
    nome: str
    endereco: str
    latitude: float
    longitude: float
    capacidade_total: int
    status: StatusEstacao = StatusEstacao.OPERACIONAL


@dataclass
class CartaoORM:
    token: str
    ultimos_digitos: str
    bandeira: str
    nome_titular: str
    validade: str
    apelido: Optional[str] = None


@dataclass
class BicicletaORM:
    id: int
    qr_code: str
    estacao_id: Optional[int] = None
    status: StatusBicicleta = StatusBicicleta.DISPONIVEL
    bloqueio_pendente: bool = False

    def apta_para_locacao(self) -> bool:
        return self.status == StatusBicicleta.DISPONIVEL


@dataclass
class LocacaoORM:
    id: int
    usuario_email: str
    bicicleta_id: int
    estacao_origem_id: int
    data_hora_inicio: datetime
    estacao_destino_id: Optional[int] = None
    data_hora_fim: Optional[datetime] = None
    duracao_minutos: Optional[int] = None
    # minutos abatidos do pacote; valor_total cobre só o excedente (RN-04/RN-05)
    minutos_pacote: int = 0
    valor_total: Optional[float] = None
    em_andamento: bool = True


@dataclass
class PagamentoORM:
    """Paga uma corrida OU a compra de um pacote: exatamente um entre
    locacao_id e pacote_id deve estar preenchido (validado no service)."""

    id: int
    valor: float
    tipo: TipoPagamento
    data_hora: datetime
    status: StatusPagamento = StatusPagamento.PENDENTE
    locacao_id: Optional[int] = None
    pacote_id: Optional[int] = None
    token_cartao: Optional[str] = None
    qr_code_pix: Optional[str] = None


@dataclass
class ReporteAvariaORM:
    id: int
    descricao: str
    data_hora: datetime
    usuario_email: str
    bicicleta_id: int
    status: StatusAvaria = StatusAvaria.PENDENTE


@dataclass
class ComprovanteORM:
    id: int
    data_emissao: datetime
    resumo_trajeto: str
    tarifa_aplicada: float
    locacao_id: int
    # None quando o pacote cobriu a corrida inteira (não houve cobrança)
    pagamento_id: Optional[int] = None


@dataclass
class EventoAuditoriaORM:
    """Histórico de alterações manuais de status (UC2, pós-condição 3).
    Não consta no diagrama de classes; ver issue [C7]."""

    id: int
    data_hora: datetime
    usuario_email: str
    tipo_entidade: Literal["BICICLETA", "ESTACAO"]
    entidade_id: int
    status_anterior: str
    status_novo: str


@dataclass
class PacoteMinutosORM:
    id: int
    usuario_email: str
    minutos_totais: int
    minutos_restantes: int
    data_validade: datetime
    # False até o pagamento da compra ser aprovado
    ativo: bool = False