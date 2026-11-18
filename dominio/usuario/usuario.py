"""
dominio/usuario/usuario.py
----------------------------------
Classe `Usuario` do diagrama: ciclista, operador de campo ou administrador.
"""

from datetime import datetime
from typing import Optional

from servicos_tecnicos.banco_de_dados import memoria
from servicos_tecnicos.banco_de_dados.enums import PapelUsuario
from servicos_tecnicos.seguranca import conferir_senha, gerar_hash


class Usuario:
    """O e-mail identifica o usuário (não há id numérico).

    Construtor do diagrama: Usuario(nome, email, cpf, papel). A senha não faz
    parte dele: entra por `definir_senha()` (ou, para quem já tem o hash
    pronto, pelo parâmetro opcional `senha_hash`).
    """

    def __init__(
        self,
        nome: str,
        email: str,
        cpf: Optional[str] = None,
        papel: PapelUsuario = PapelUsuario.CICLISTA,
        *,
        senha_hash: Optional[str] = None,
        telefone: Optional[str] = None,
        endereco: Optional[str] = None,
    ):
        self.nome = nome
        self.email = email
        # cpf/telefone só existem para ciclistas; administrador não os possui
        self.cpf = cpf
        self.papel = papel
        self.senha_hash = senha_hash
        self.telefone = telefone
        self.endereco = endereco

    def __repr__(self) -> str:
        return f"Usuario(nome={self.nome!r}, email={self.email!r}, papel={self.papel!r})"

    def definir_senha(self, senha_texto: str) -> None:
        """Guarda só o hash da senha, nunca o texto."""
        self.senha_hash = gerar_hash(senha_texto)

    def autenticar(self, senha: str) -> bool:
        """Confere a senha em texto contra o hash guardado."""
        if not self.senha_hash:
            return False
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
