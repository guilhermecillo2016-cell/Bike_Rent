"""
dominio/comprovante/comprovante_viagem.py
-------------------------------------------------
Classe `ComprovanteViagem` do diagrama: comprovante digital da corrida.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from dominio.locacao.locacao import Locacao
    from dominio.pagamento.pagamento import Pagamento


class ComprovanteViagem:
    """Construtor do diagrama: ComprovanteViagem(locacao, pagamento).

    O resumo do trajeto e a tarifa aplicada saem da própria locação
    (que já deve estar encerrada). `pagamento` é None quando o pacote
    cobriu a corrida inteira ou quando a cobrança não pôde ser feita. O
    id (`id_comprovante`) é dado pelo repositório.
    """

    def __init__(
        self,
        locacao: "Locacao",
        pagamento: Optional["Pagamento"] = None,
        *,
        id_comprovante: Optional[int] = None,
    ):
        self.id_comprovante = id_comprovante
        self.locacao = locacao
        self.pagamento = pagamento
        self.data_emissao = datetime.now()
        self.resumo_trajeto = f"{locacao.estacao_origem.nome} → {locacao.estacao_destino.nome}"
        self.tarifa_aplicada = locacao.valor_total or 0.0

    def __repr__(self) -> str:
        return (
            f"ComprovanteViagem(id_comprovante={self.id_comprovante!r}, "
            f"locacao_id={self.locacao_id!r}, pagamento_id={self.pagamento_id!r})"
        )

    # --- nomes antigos, só leitura ----------------------------------------
    @property
    def id(self) -> Optional[int]:
        return self.id_comprovante

    @property
    def locacao_id(self) -> Optional[int]:
        return self.locacao.id_locacao

    @property
    def pagamento_id(self) -> Optional[int]:
        return getattr(self.pagamento, "id", None)
