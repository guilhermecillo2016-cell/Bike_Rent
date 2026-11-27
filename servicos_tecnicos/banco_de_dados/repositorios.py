"""
servicos_tecnicos/banco_de_dados/repositorios.py
--------------------------------------------------
Interfaces dos repositórios ([A13]). Os services conhecem só estes contratos;
quem os implementa é a camada de persistência (hoje, em memória, nos
`repository_*.py`; na [A16]/[A17]/[B19]/[C16], também no PostgreSQL).

Regra de persistência
=====================
Alterar um objeto devolvido pelo repositório **não** é a forma suportada de
persistir a alteração. Depois de mudar o estado de um objeto (status da
bicicleta, locação encerrada, saldo do pacote, status do pagamento etc.),
o service chama `salvar(obj)`. Na implementação em memória o efeito é o
mesmo de antes (o objeto já está guardado por referência), mas numa
implementação com banco de dados é o `salvar()` que grava a mudança.

`create(...)` monta o objeto, gera o id e já o guarda; `salvar(obj)` insere
(se o objeto ainda não tem id) ou atualiza (se já tem).

As classes de domínio não importam este módulo: só os services e a fábrica.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING, Generic, Literal, Optional, TypeVar

if TYPE_CHECKING:
    from dominio.auditoria.evento_auditoria import EventoAuditoria
    from dominio.avaria.reporte_avaria import ReporteAvaria
    from dominio.bicicleta.bicicleta import Bicicleta
    from dominio.comprovante.comprovante_viagem import ComprovanteViagem
    from dominio.estacao.estacao import Estacao
    from dominio.locacao.locacao import Locacao
    from dominio.pacote.pacote_minutos import PacoteMinutos
    from dominio.pagamento.cartao import Cartao
    from dominio.pagamento.pagamento import Pagamento
    from dominio.usuario.usuario import Usuario
    from servicos_tecnicos.banco_de_dados.enums import TipoPagamento

T = TypeVar("T")


class Repositorio(ABC, Generic[T]):
    """Contrato comum. Mudou o objeto? Chame `salvar(obj)` (ver o módulo)."""

    @abstractmethod
    def salvar(self, obj: T) -> T:
        """Grava o objeto (insere se novo, atualiza se já existe) e o devolve."""

    @abstractmethod
    def list_all(self) -> list[T]:
        """Todos os objetos guardados."""


class RepositorioUsuario(Repositorio["Usuario"]):
    """Usuário é identificado pelo e-mail até a [A23] trazer `id_usuario`."""

    @abstractmethod
    def create(self, usuario: "Usuario") -> "Usuario": ...

    @abstractmethod
    def get_by_email(self, email: str) -> Optional["Usuario"]: ...

    @abstractmethod
    def get_by_cpf(self, cpf: str) -> Optional["Usuario"]: ...


class RepositorioEstacao(Repositorio["Estacao"]):
    @abstractmethod
    def create(
        self, nome: str, endereco: str, latitude: float, longitude: float,
        capacidade_total: int,
    ) -> "Estacao": ...

    @abstractmethod
    def get_by_id(self, estacao_id: int) -> Optional["Estacao"]: ...


class RepositorioBicicleta(Repositorio["Bicicleta"]):
    @abstractmethod
    def create(self, estacao: Optional["Estacao"]) -> "Bicicleta": ...

    @abstractmethod
    def get_by_id(self, bicicleta_id: int) -> Optional["Bicicleta"]: ...

    @abstractmethod
    def get_by_qr(self, qr_code: str) -> Optional["Bicicleta"]: ...

    @abstractmethod
    def list_by_estacao(self, estacao_id: int) -> list["Bicicleta"]: ...


class RepositorioLocacao(Repositorio["Locacao"]):
    @abstractmethod
    def create(
        self, usuario: "Usuario", bicicleta: "Bicicleta", estacao_origem: "Estacao",
    ) -> "Locacao": ...

    @abstractmethod
    def get_by_id(self, locacao_id: int) -> Optional["Locacao"]: ...

    @abstractmethod
    def get_ativa_by_usuario(self, usuario_email: str) -> Optional["Locacao"]: ...


class RepositorioPacote(Repositorio["PacoteMinutos"]):
    @abstractmethod
    def create(
        self, usuario: "Usuario", minutos_totais: int, data_validade: datetime,
    ) -> "PacoteMinutos": ...

    @abstractmethod
    def get_by_id(self, pacote_id: int) -> Optional["PacoteMinutos"]: ...

    @abstractmethod
    def list_by_email(self, usuario_email: str) -> list["PacoteMinutos"]: ...


class RepositorioPagamento(Repositorio["Pagamento"]):
    @abstractmethod
    def create(
        self, valor: float, tipo: "TipoPagamento", locacao: Optional["Locacao"] = None,
        pacote: Optional["PacoteMinutos"] = None, token_cartao: Optional[str] = None,
    ) -> "Pagamento": ...

    @abstractmethod
    def get_by_id(self, pagamento_id: int) -> Optional["Pagamento"]: ...


class RepositorioCartao(Repositorio["Cartao"]):
    """Cartões por e-mail do dono, até a [C15] ligar Cartao ao Usuario por
    objeto e a [A23] trazer `id_cartao`. O token identifica o cartão."""

    @abstractmethod
    def add_cartao(self, email_usuario: str, cartao: "Cartao") -> "Cartao": ...

    @abstractmethod
    def list_cartoes(self, email_usuario: str) -> list["Cartao"]: ...

    @abstractmethod
    def get_cartao(self, email_usuario: str, token: str) -> Optional["Cartao"]: ...

    @abstractmethod
    def remover_cartao(self, email_usuario: str, cartao: "Cartao") -> None: ...

    @abstractmethod
    def get_credito_by_email(self, email_usuario: str) -> Optional["Cartao"]: ...

    @abstractmethod
    def get_debito_by_email(self, email_usuario: str) -> Optional["Cartao"]: ...


class RepositorioAvaria(Repositorio["ReporteAvaria"]):
    @abstractmethod
    def create(
        self, bicicleta: "Bicicleta", usuario: "Usuario", descricao: str,
    ) -> "ReporteAvaria": ...

    @abstractmethod
    def get_by_id(self, avaria_id: int) -> Optional["ReporteAvaria"]: ...

    @abstractmethod
    def list_by_bicicleta(self, bicicleta_id: int) -> list["ReporteAvaria"]: ...


class RepositorioComprovante(Repositorio["ComprovanteViagem"]):
    @abstractmethod
    def create(
        self, locacao: "Locacao", pagamento: Optional["Pagamento"] = None,
    ) -> "ComprovanteViagem": ...

    @abstractmethod
    def get_by_id(self, comprovante_id: int) -> Optional["ComprovanteViagem"]: ...

    @abstractmethod
    def get_by_locacao(self, locacao_id: int) -> Optional["ComprovanteViagem"]: ...


class RepositorioAuditoria(Repositorio["EventoAuditoria"]):
    """Eventos só são acrescentados, nunca alterados."""

    @abstractmethod
    def create(
        self, usuario_email: str, tipo_entidade: Literal["BICICLETA", "ESTACAO"],
        entidade_id: int, status_anterior: str, status_novo: str,
    ) -> "EventoAuditoria": ...

    @abstractmethod
    def get_by_id(self, auditoria_id: int) -> Optional["EventoAuditoria"]: ...
