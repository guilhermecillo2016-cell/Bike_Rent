"""
dominio/estacao/estacao.py
----------------------------------
Classe `Estacao` do diagrama. É a dona da associação com as bicicletas.
"""

from typing import TYPE_CHECKING, Optional

from dominio.erros import ConflitoDeRegra
from dominio.geolocalizacao.geolocalizacao import Geolocalizacao
from servicos_tecnicos.banco_de_dados.enums import StatusEstacao

if TYPE_CHECKING:
    from dominio.bicicleta.bicicleta import Bicicleta


class Estacao:
    """Estação. É a ÚNICA dona da associação com as bicicletas: a lista
    `bicicletas` é a fonte da verdade e `Bicicleta.estacao` só espelha.

    Construtor do diagrama: Estacao(id_estacao, nome, endereco, capacidade).
    A localização (Geolocalizacao, composição) entra como parâmetro opcional.
    """

    def __init__(
        self,
        id_estacao: int,
        nome: str,
        endereco: str,
        capacidade: int,
        *,
        localizacao: Optional[Geolocalizacao] = None,
        status: StatusEstacao = StatusEstacao.OPERACIONAL,
    ):
        self.id_estacao = id_estacao
        self.nome = nome
        self.endereco = endereco
        self.capacidade_total = capacidade
        # Objeto de valor: no banco vira as colunas latitude e longitude.
        self.localizacao = localizacao
        self.status = status
        self.bicicletas: list["Bicicleta"] = []

    def __repr__(self) -> str:
        return (
            f"Estacao(id_estacao={self.id_estacao!r}, nome={self.nome!r}, "
            f"capacidade_total={self.capacidade_total!r}, status={self.status!r})"
        )

    @property
    def id(self) -> int:
        return self.id_estacao

    @property
    def latitude(self) -> Optional[float]:
        return self.localizacao.latitude if self.localizacao is not None else None

    @property
    def longitude(self) -> Optional[float]:
        return self.localizacao.longitude if self.localizacao is not None else None

    def distancia_ate_em_metros(self, outra: "Estacao") -> float:
        return self.localizacao.calcular_distancia_em_metros(outra.localizacao)

    @property
    def vagas_disponiveis(self) -> int:
        """Derivado: capacidade menos as bicicletas que estão aqui."""
        return self.capacidade_total - len(self.bicicletas)

    def possui_vaga_livre(self) -> bool:
        return self.status == StatusEstacao.OPERACIONAL and self.vagas_disponiveis > 0

    def quantidade_bicicletas_disponiveis(self) -> int:
        return sum(1 for b in self.bicicletas if b.apta_para_locacao())

    def possui_bicicleta_disponivel(self) -> bool:
        return self.quantidade_bicicletas_disponiveis() > 0

    def exigir_vaga_livre(self) -> None:
        """409 se não está OPERACIONAL (bloqueada ou em manutenção não recebe
        nem libera bicicletas) ou se está lotada."""
        if self.status != StatusEstacao.OPERACIONAL:
            raise ConflitoDeRegra("A estação não está operacional")
        if self.vagas_disponiveis <= 0:
            raise ConflitoDeRegra("A estação está lotada")

    def adicionar_bicicleta(self, bicicleta: "Bicicleta") -> None:
        """Guarda a bicicleta na lista SEM checar vaga nem status (usado no
        cadastro; quem quer a regra completa usa alocar_bicicleta)."""
        self.bicicletas.append(bicicleta)
        bicicleta._entrar_na_estacao(self)

    def alocar_bicicleta(self, bicicleta: "Bicicleta") -> None:
        """Estaciona a bicicleta aqui. 409 se a estação não aceita ou se a
        bicicleta já está em uma estação."""
        self.exigir_vaga_livre()
        if bicicleta.estacao is not None:
            raise ConflitoDeRegra("A bicicleta já está em uma estação")
        self.adicionar_bicicleta(bicicleta)

    def remover_bicicleta(self, bicicleta: "Bicicleta") -> None:
        """Tira a bicicleta daqui. 409 se a estação não está operacional ou
        se a bicicleta não está nela."""
        if self.status != StatusEstacao.OPERACIONAL:
            raise ConflitoDeRegra("A estação não está operacional")
        if not any(b is bicicleta for b in self.bicicletas):
            raise ConflitoDeRegra("A bicicleta não está nesta estação")
        self.bicicletas[:] = [b for b in self.bicicletas if b is not bicicleta]
        bicicleta._sair_da_estacao()

    def set_status(self, novo_status: StatusEstacao) -> None:
        self.status = StatusEstacao(novo_status)
