"""
servicos_tecnicos/banco_de_dados/repository_bicicleta.py
-----------------------------------------------------------
Armazenamento em memória das bicicletas. Quem guarda a lista das
bicicletas de cada estação é a própria Estacao (fonte da verdade);
Bicicleta.estacao_id só espelha essa associação.

`RepositorioBicicletaMemoria` implementa a interface `RepositorioBicicleta`
([A13]). As funções de módulo continuam existindo como fachada da instância
padrão (`padrao`).
"""

import uuid
from typing import Optional

from servicos_tecnicos.banco_de_dados import memoria
from servicos_tecnicos.banco_de_dados.repositorios import RepositorioBicicleta
from dominio.bicicleta.bicicleta import Bicicleta
from dominio.estacao.estacao import Estacao


class RepositorioBicicletaMemoria(memoria.ColecaoPorId, RepositorioBicicleta):
    colecao = "bicicletas"
    atributo_id = "id_bicicleta"

    def _novo_qr_code(self) -> str:
        """Código aleatório (não dá para adivinhar a partir do id) e único."""
        while True:
            qr_code = "BIKE-" + uuid.uuid4().hex[:12].upper()
            if self.get_by_qr(qr_code) is None:
                return qr_code

    def create(self, estacao: Optional[Estacao]) -> Bicicleta:
        """Cria a bicicleta já estacionada em `estacao` (ou solta, se None)."""
        bicicleta = Bicicleta(memoria.proximo_id("bicicletas"), self._novo_qr_code())
        self.salvar(bicicleta)
        if estacao is not None:
            estacao.adicionar_bicicleta(bicicleta)
        return bicicleta

    def get_by_qr(self, qr_code: str) -> Optional[Bicicleta]:
        return next((b for b in self.list_all() if b.qr_code == qr_code), None)

    def list_by_estacao(self, estacao_id: int) -> list[Bicicleta]:
        """Quem sabe quais bicicletas estão na estação é a própria Estacao;
        aqui só se pergunta a ela (na ordem de cadastro, como sempre)."""
        estacao = memoria.estacoes.get(estacao_id)
        if estacao is None:
            return []
        return sorted(estacao.bicicletas, key=lambda b: b.id)


padrao = RepositorioBicicletaMemoria()


# --- Fachada de módulo (assinaturas de sempre) ---------------------------
def _novo_qr_code() -> str:
    return padrao._novo_qr_code()


def create(estacao: Optional[Estacao]) -> Bicicleta:
    return padrao.create(estacao)


def get_by_id(bicicleta_id: int) -> Optional[Bicicleta]:
    return padrao.get_by_id(bicicleta_id)


def get_by_qr(qr_code: str) -> Optional[Bicicleta]:
    return padrao.get_by_qr(qr_code)


def list_all() -> list[Bicicleta]:
    return padrao.list_all()


def list_by_estacao(estacao_id: int) -> list[Bicicleta]:
    return padrao.list_by_estacao(estacao_id)


def salvar(bicicleta: Bicicleta) -> Bicicleta:
    return padrao.salvar(bicicleta)
