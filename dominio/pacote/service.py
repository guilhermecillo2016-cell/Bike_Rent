"""Regras do pacote de minutos (RF-10, RN-04, RN-05).

- Compra por cartão: o pacote nasce INATIVO e SEM saldo; só se o pagamento for
  APROVADO ele é ativado e o saldo creditado (RF-10).
- Pacote vencido ou zerado deixa de contar (ativo=False), atualizado de forma
  "preguiçosa" sempre que o pacote é lido.
- `abater_minutos` consome primeiro o pacote que vence antes e devolve quantos
  minutos conseguiu abater; o restante é cobrado no cartão pela [B5] (RN-05).
"""

from datetime import datetime, timedelta

from fastapi import HTTPException, status

from dominio.pacote.schemas import ItemCatalogo
from dominio.pagamento.service import PagamentoService
from servicos_tecnicos.banco_de_dados import repository_pacote
from servicos_tecnicos.banco_de_dados.enums import StatusPagamento

# Catálogo fixo. Preços e validades são valores provisórios: ajuste às regras.
CATALOGO_PACOTES: tuple[ItemCatalogo, ...] = (
    ItemCatalogo(id=1, minutos=30, preco=15.00, validade_dias=7),
    ItemCatalogo(id=2, minutos=60, preco=27.00, validade_dias=15),
    ItemCatalogo(id=3, minutos=120, preco=50.00, validade_dias=30),
)


class PacoteService:
    def __init__(self, pagamento_service, pacote_repo=None, relogio=None):
        self.pagamento_service = pagamento_service
        self.pacote_repo = pacote_repo or repository_pacote
        self.relogio = relogio or datetime.now  # injetável para testar validade

    # --- Catálogo e compra --------------------------------------------
    def listar_catalogo(self):
        return list(CATALOGO_PACOTES)

    def comprar_pacote(self, email, item_id):
        """Devolve (pacote, pagamento). Recusa NÃO lança exceção: o pacote fica
        inativo e sem saldo, e o pagamento volta com status RECUSADO."""
        item = self._obter_item(item_id)
        self.pagamento_service.exigir_cartao_credito(email)  # RN-06, antes de criar

        validade = self.relogio() + timedelta(days=item.validade_dias)
        pacote = self.pacote_repo.create(email, item.minutos, validade)

        pagamento = self.pagamento_service.cobrar_pacote(email, item.preco, pacote.id)
        if pagamento.status == StatusPagamento.APROVADO:
            pacote.minutos_restantes = pacote.minutos_totais
            pacote.ativo = True
        return pacote, pagamento

    def listar_pacotes(self, email):
        pacotes = self.pacote_repo.list_by_email(email)
        for pacote in pacotes:
            self._atualizar_situacao(pacote)
        return pacotes

    # --- Contratos para a locação ([B4]/[B5]) -------------------------
    def saldo_minutos(self, email) -> int:
        """Soma `minutos_restantes` dos pacotes ativos e dentro da validade."""
        return sum(p.minutos_restantes for p in self._pacotes_validos(email))

    def abater_minutos(self, email, minutos) -> int:
        """Consome minutos dos pacotes válidos, o que vence primeiro antes.

        Devolve quantos minutos conseguiu abater (pode ser menos que o pedido).
        """
        if minutos < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Minutos a abater não pode ser negativo",
            )
        restante = minutos
        for pacote in sorted(
            self._pacotes_validos(email), key=lambda p: (p.data_validade, p.id)
        ):
            if restante == 0:
                break
            consumo = min(pacote.minutos_restantes, restante)
            pacote.minutos_restantes -= consumo
            restante -= consumo
            self._atualizar_situacao(pacote)  # zerou -> ativo=False
        return minutos - restante

    # --- Internos -----------------------------------------------------
    @staticmethod
    def _obter_item(item_id):
        for item in CATALOGO_PACOTES:
            if item.id == item_id:
                return item
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item do catálogo não encontrado",
        )

    def _atualizar_situacao(self, pacote):
        """Pacote ativo que venceu ou zerou passa a ativo=False."""
        if pacote.ativo and (
            pacote.minutos_restantes <= 0 or pacote.data_validade <= self.relogio()
        ):
            pacote.ativo = False

    def _pacotes_validos(self, email):
        pacotes = self.pacote_repo.list_by_email(email)
        for pacote in pacotes:
            self._atualizar_situacao(pacote)
        return [p for p in pacotes if p.ativo]


# ----------------------------------------------------------------------
# API em nível de módulo, no padrão dos demais services do projeto:
#   from dominio.pacote import service as pacote_service
#   pacote_service.saldo_minutos(email)
# ----------------------------------------------------------------------
def _servico() -> PacoteService:
    return PacoteService(PagamentoService())


def listar_catalogo():
    return _servico().listar_catalogo()


def comprar_pacote(email, item_id):
    return _servico().comprar_pacote(email, item_id)


def listar_pacotes(email):
    return _servico().listar_pacotes(email)


def saldo_minutos(email) -> int:
    return _servico().saldo_minutos(email)


def abater_minutos(email, minutos) -> int:
    return _servico().abater_minutos(email, minutos)