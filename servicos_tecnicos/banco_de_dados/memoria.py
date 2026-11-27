"""
servicos_tecnicos/banco_de_dados/memoria.py
----------------------------------------------
Camada técnica de PERSISTÊNCIA (caixa "BancoDeDados" no diagrama) —
por enquanto SEM banco de dados real e SEM persistência: os dados
ficam só em memória (dicionários Python) e são perdidos a cada
reinício da aplicação.

Quando um banco de verdade entrar, só esse arquivo (e os
repository_*.py que o usam) precisam mudar. Só os repositórios em memória
(repository_*.py) mexem nestes dicionários; os services usam as interfaces
de repositorios.py, obtidas pela fabrica.py.
"""

import itertools
from collections import defaultdict

# username/email -> Usuario
usuarios: dict[str, "object"] = {}

# id da estação -> Estacao
estacoes: dict[int, "object"] = {}

# id da bicicleta -> Bicicleta
bicicletas: dict[int, "object"] = {}

# id do pacote -> PacoteMinutos
pacotes: dict[int, "object"] = {}

# email do usuário -> lista de Cartao
cartoes: dict[str, list] = {}

# id da locação -> Locacao
locacoes: dict[int, "object"] = {}

# id do pagamento -> Pagamento
pagamentos: dict[int, "object"] = {}

# id do reporte -> ReporteAvaria
avarias: dict[int, "object"] = {}

# id do comprovante -> ComprovanteViagem
comprovantes: dict[int, "object"] = {}

# id do evento -> EventoAuditoria
eventos_auditoria: dict[int, "object"] = {}

# Contador de ids inteiros por coleção (1, 2, 3, ...), no lugar da
# sequência/auto-incremento que um banco real faria.
_contadores = defaultdict(lambda: itertools.count(1))


def proximo_id(colecao: str) -> int:
    return next(_contadores[colecao])


class ColecaoPorId:
    """Base das implementações em memória dos repositórios ([A13]): um dos
    dicionários acima (id -> objeto). A subclasse diz qual dicionário
    (`colecao`) e o nome do atributo de id do objeto (`atributo_id`).

    O dicionário é buscado a cada chamada (e não guardado na instância) para
    continuar valendo se alguém o trocar inteiro."""

    colecao: str
    atributo_id: str

    def _dados(self) -> dict:
        return globals()[self.colecao]

    def salvar(self, obj):
        """Insere (gera o id se o objeto ainda não tem) ou atualiza."""
        if getattr(obj, self.atributo_id) is None:
            setattr(obj, self.atributo_id, proximo_id(self.colecao))
        self._dados()[getattr(obj, self.atributo_id)] = obj
        return obj

    def get_by_id(self, id_):
        return self._dados().get(id_)

    def list_all(self) -> list:
        return list(self._dados().values())
