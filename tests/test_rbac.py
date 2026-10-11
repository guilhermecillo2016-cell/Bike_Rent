"""
tests/test_rbac.py
--------------------
Testes da A2 (RBAC): a dependency requer_papel e o cadastro de operador.

Rodar da raiz do projeto:
    python -m unittest discover -s tests -t . -v
(também funcionam com pytest, se estiver instalado)

As dependencies são chamadas direto com o token, sem subir servidor nem
TestClient. A memória é global, então ela é limpa antes de cada teste.
"""

import unittest
from datetime import timedelta

from fastapi import HTTPException
from jose import jwt
from pydantic import ValidationError

from dominio.usuario import service
from dominio.usuario.schemas import AdminCreate, OperadorCreate
from servicos_tecnicos.banco_de_dados import memoria
from servicos_tecnicos.banco_de_dados.enums import PapelUsuario

ADMIN = PapelUsuario.ADMINISTRADOR
OPERADOR = PapelUsuario.OPERADOR_CAMPO
CICLISTA = PapelUsuario.CICLISTA


def _token(email: str) -> str:
    return service.create_access_token({"sub": email})


class RbacTestCase(unittest.TestCase):
    def setUp(self):
        memoria.usuarios.clear()
        service.register_admin(AdminCreate(nome="Ana", email="admin@x.com", senha="123456"))
        service.register_operador(OperadorCreate(nome="Olga", email="op@x.com", senha="123456"))
        memoria.usuarios["ciclista@x.com"] = service.UsuarioORM(
            nome="Cid",
            email="ciclista@x.com",
            senha_hash=service.get_password_hash("123456"),
            papel=CICLISTA,
        )

    def passa(self, dependency, email):
        return dependency(_token(email))

    def barra(self, dependency, token, codigo):
        with self.assertRaises(HTTPException) as ctx:
            dependency(token)
        self.assertEqual(ctx.exception.status_code, codigo)
        return ctx.exception


class RequerPapelTests(RbacTestCase):
    def test_somente_admin(self):
        dep = service.requer_papel(ADMIN)
        self.assertEqual(self.passa(dep, "admin@x.com").papel, ADMIN)
        self.barra(dep, _token("op@x.com"), 403)
        self.barra(dep, _token("ciclista@x.com"), 403)

    def test_somente_operador_barra_admin_e_ciclista(self):
        dep = service.requer_papel(OPERADOR)
        self.assertEqual(self.passa(dep, "op@x.com").papel, OPERADOR)
        self.barra(dep, _token("admin@x.com"), 403)
        self.barra(dep, _token("ciclista@x.com"), 403)

    def test_equipe_aceita_admin_e_operador_mas_nao_ciclista(self):
        dep = service.requer_papel(ADMIN, OPERADOR)
        self.assertEqual(self.passa(dep, "admin@x.com").papel, ADMIN)
        self.assertEqual(self.passa(dep, "op@x.com").papel, OPERADOR)
        self.barra(dep, _token("ciclista@x.com"), 403)

    def test_mensagem_de_403_diz_quem_pode(self):
        erro = self.barra(service.requer_papel(ADMIN), _token("op@x.com"), 403)
        self.assertEqual(erro.detail, "Acesso restrito a administradores")
        erro = self.barra(service.requer_papel(ADMIN, OPERADOR), _token("ciclista@x.com"), 403)
        self.assertIn("operadores de campo", erro.detail)

    def test_atalho_antigo_get_current_admin_user_continua_valendo(self):
        self.assertEqual(self.passa(service.get_current_admin_user, "admin@x.com").papel, ADMIN)
        self.barra(service.get_current_admin_user, _token("op@x.com"), 403)

    def test_papel_vem_do_cadastro_e_nao_do_token(self):
        # token só leva o e-mail: promover/rebaixar vale na próxima requisição
        token = _token("op@x.com")
        memoria.usuarios["op@x.com"].papel = CICLISTA
        self.barra(service.requer_papel(OPERADOR), token, 403)

    def test_configuracao_invalida_falha_na_criacao(self):
        with self.assertRaises(ValueError):
            service.requer_papel()
        with self.assertRaises(ValueError):
            service.requer_papel("CHEFE")


class TokenInvalidoTests(RbacTestCase):
    def test_tokens_ruins_dao_401(self):
        dep = service.requer_papel(ADMIN)
        vencido = service.create_access_token({"sub": "admin@x.com"}, timedelta(minutes=-1))
        sem_sub = jwt.encode({"x": 1}, service.SECRET_KEY, algorithm=service.ALGORITHM)
        outra_chave = jwt.encode({"sub": "admin@x.com"}, "outra", algorithm=service.ALGORITHM)
        fantasma = _token("naoexiste@x.com")
        for token in ("", "lixo", vencido, sem_sub, outra_chave, fantasma):
            with self.subTest(token=token[:20]):
                self.barra(dep, token, 401)


class CadastroOperadorTests(RbacTestCase):
    def test_operador_nasce_com_papel_certo_e_sem_dados_de_ciclista(self):
        op = memoria.usuarios["op@x.com"]
        self.assertEqual(op.papel, OPERADOR)
        self.assertEqual(op.nome, "Olga")
        self.assertIsNone(op.cpf)
        self.assertIsNone(op.telefone)
        self.assertNotEqual(op.senha_hash, "123456")

    def test_email_duplicado_e_recusado_entre_todos_os_papeis(self):
        for email in ("op@x.com", "admin@x.com", "ciclista@x.com"):
            with self.subTest(email=email):
                with self.assertRaises(HTTPException) as ctx:
                    service.register_operador(OperadorCreate(nome="X", email=email, senha="123456"))
                self.assertEqual(ctx.exception.status_code, 400)

    def test_schema_exige_nome_email_valido_e_senha_minima(self):
        for dados in (
            {"email": "a@x.com", "senha": "123456"},
            {"nome": "A", "email": "nao-e-email", "senha": "123456"},
            {"nome": "A", "email": "a@x.com", "senha": "123"},
        ):
            with self.subTest(dados=dados):
                with self.assertRaises(ValidationError):
                    OperadorCreate(**dados)


if __name__ == "__main__":
    unittest.main()
