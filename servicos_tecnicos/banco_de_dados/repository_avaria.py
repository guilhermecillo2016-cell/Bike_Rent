"""
servicos_tecnicos/banco_de_dados/repository_avaria.py
-----------------------------------------------------------
Armazenamento em memória dos reportes de avaria feitos pelo ciclista
ao encerrar a corrida. A mudança de status da bicicleta para
EM_MANUTENCAO é feita pelo service, não aqui.

`RepositorioAvariaMemoria` implementa a interface `RepositorioAvaria`
([A13]). As funções de módulo continuam existindo como fachada da instância
padrão (`padrao`).
"""

from typing import Optional

from servicos_tecnicos.banco_de_dados import memoria
from servicos_tecnicos.banco_de_dados.repositorios import RepositorioAvaria
from dominio.avaria.reporte_avaria import ReporteAvaria
from dominio.bicicleta.bicicleta import Bicicleta
from dominio.usuario.usuario import Usuario


class RepositorioAvariaMemoria(memoria.ColecaoPorId, RepositorioAvaria):
    colecao = "avarias"
    atributo_id = "id_reporte"

    def create(self, bicicleta: Bicicleta, usuario: Usuario, descricao: str) -> ReporteAvaria:
        avaria = ReporteAvaria(
            bicicleta, usuario, descricao,
            id_reporte=memoria.proximo_id("avarias"),
        )
        return self.salvar(avaria)

    def list_by_bicicleta(self, bicicleta_id: int) -> list[ReporteAvaria]:
        return [a for a in self.list_all() if a.bicicleta_id == bicicleta_id]


padrao = RepositorioAvariaMemoria()


# --- Fachada de módulo (assinaturas de sempre) ---------------------------
def create(
        bicicleta: Bicicleta,
        usuario: Usuario,
        descricao: str,
        ) -> ReporteAvaria:
    return padrao.create(bicicleta, usuario, descricao)


def get_by_id(avaria_id: int) -> Optional[ReporteAvaria]:
    return padrao.get_by_id(avaria_id)


def list_all() -> list[ReporteAvaria]:
    return padrao.list_all()


def list_by_bicicleta(bicicleta_id: int) -> list[ReporteAvaria]:
    return padrao.list_by_bicicleta(bicicleta_id)


def salvar(avaria: ReporteAvaria) -> ReporteAvaria:
    return padrao.salvar(avaria)
