"""
tests/test_cadastro.py
------------------------
Testes do cadastro de ciclista: e-mail e CPF não podem se repetir.

Rodar da raiz do projeto:
    python -m unittest discover -s tests -t . -v
"""

import unittest

from fastapi import HTTPException

from dominio.usuario import service
from dominio.usuario.schemas import AdminCreate, OperadorCreate, UsuarioCreate
from servicos_tecnicos.banco_de_dados import memoria
from servicos_tecnicos.banco_de_dados import repository_usuario as repo

CPF_A = "529.982.247-25"
CPF_B = "111.444.777-35"


def _ciclista(email="a@x.com", cpf=CPF_A):
    return service.register_user(
        UsuarioCreate(nome="Cid", email=email, senha="123456", cpf=cpf, telefone="48999999999")
    )


class CadastroCpfTests(unittest.TestCase):
    def setUp(self):
        memoria.usuarios.clear()

    def erro(self, funcao, *args, **kwargs):
        with self.assertRaises(HTTPException) as ctx:
            funcao(*args, **kwargs)
        return ctx.exception

    def test_os_cpfs_do_teste_sao_validos(self):
        self.assertTrue(service.cpf_valido(CPF_A))
        self.assertTrue(service.cpf_valido(CPF_B))

    def test_cadastro_normal_guarda_so_os_numeros(self):
        usuario = _ciclista()
        self.assertEqual(usuario.cpf, "52998224725")

    def test_mesmo_cpf_com_outro_email_e_recusado(self):
        _ciclista("a@x.com")
        erro = self.erro(_ciclista, "b@x.com")
        self.assertEqual(erro.status_code, 400)
        self.assertEqual(erro.detail, "Já existe uma conta com esse CPF")
        self.assertEqual(len(memoria.usuarios), 1)

    def test_mesmo_cpf_com_ou_sem_pontuacao_e_o_mesmo(self):
        _ciclista("a@x.com", "529.982.247-25")
        for formato in ("52998224725", "529.982.247-25", "529 982 247 25"):
            with self.subTest(formato=formato):
                erro = self.erro(_ciclista, "b@x.com", formato)
                self.assertEqual(erro.detail, "Já existe uma conta com esse CPF")

    def test_cpfs_diferentes_convivem(self):
        _ciclista("a@x.com", CPF_A)
        _ciclista("b@x.com", CPF_B)
        self.assertEqual(len(memoria.usuarios), 2)

    def test_email_repetido_continua_recusado_com_a_mensagem_do_email(self):
        _ciclista("a@x.com", CPF_A)
        erro = self.erro(_ciclista, "a@x.com", CPF_B)
        self.assertEqual(erro.status_code, 400)
        self.assertEqual(erro.detail, "Já existe uma conta com esse e-mail")

    def test_cpf_invalido_continua_sendo_recusado_primeiro(self):
        erro = self.erro(_ciclista, "a@x.com", "123.456.789-00")
        self.assertEqual(erro.detail, "CPF inválido")

    def test_equipe_sem_cpf_nao_conta_como_repetida_nem_bloqueia_ninguem(self):
        service.register_admin(AdminCreate(nome="Ana", email="adm@x.com", senha="123456"))
        service.register_admin(AdminCreate(nome="Ana 2", email="adm2@x.com", senha="123456"))
        service.register_operador(OperadorCreate(nome="Olga", email="op@x.com", senha="123456"))
        _ciclista("a@x.com", CPF_A)
        self.assertEqual(len(memoria.usuarios), 4)

    def test_get_by_cpf(self):
        usuario = _ciclista()
        self.assertIs(repo.get_by_cpf("52998224725"), usuario)
        self.assertIsNone(repo.get_by_cpf("11144477735"))
        self.assertIsNone(repo.get_by_cpf(""))
        self.assertIsNone(repo.get_by_cpf(None))


if __name__ == "__main__":
    unittest.main()
