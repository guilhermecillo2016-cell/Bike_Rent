"""
dominio/usuario/usuario.py
----------------------------------
Classe `Usuario` do diagrama: ciclista, operador de campo ou administrador.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from servicos_tecnicos.banco_de_dados import memoria
from servicos_tecnicos.banco_de_dados.enums import PapelUsuario
from servicos_tecnicos.seguranca import conferir_senha


@dataclass
class Usuario:
    nome: str
    email: str
    senha_hash: str
    papel: PapelUsuario
    # cpf/telefone só existem para ciclistas; administrador não os possui
    cpf: Optional[str] = None
    telefone: Optional[str] = None
    endereco: Optional[str] = None

    def autenticar(self, senha: str) -> bool:
        """Confere a senha em texto contra o hash guardado."""
        return conferir_senha(senha, self.senha_hash)

    def get_papel(self) -> PapelUsuario:
        return self.papel

    def possui_cartao_valido(self) -> bool:
        """RN-06: tem ao menos um cartão de crédito vinculado."""
        return any(c.tipo == "CARTAO_CREDITO" for c in memoria.cartoes.get(self.email, []))

    def tem_pacote_minutos_ativo(self, agora: Optional[datetime] = None) -> bool:
        """Tem pacote ativo, com saldo e dentro da validade."""
        agora = agora or datetime.now()
        return any(
            p.usuario_email == self.email
            and p.ativo
            and p.minutos_restantes > 0
            and p.data_validade > agora
            for p in memoria.pacotes.values()
        )
