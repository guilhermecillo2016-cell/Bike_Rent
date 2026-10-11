"""
tests/test_bicicleta.py
-------------------------
Testes da A3 (cadastro de bicicleta, QR Code e status) e do núcleo da A4
que ela usa (vaga livre e estação operacional).

Rodar da raiz do projeto:
    python -m unittest discover -s tests -t . -v
"""

import unittest
from types import SimpleNamespace
from unittest import mock

from fastapi import HTTPException
from pydantic import ValidationError

from dominio.bicicleta import service
from dominio.bicicleta.schemas import BicicletaCreate
from dominio.estacao import service as estacao_service
from dominio.estacao.schemas import EstacaoCreate
from servicos_tecnicos.banco_de_dados import memoria
from servicos_tecnicos.banco_de_dados import repository_bicicleta as repo
from servicos_tecnicos.banco_de_dados.enums import StatusBicicleta, StatusEstacao


def _estacao(capacidade=3, status=StatusEstacao.OPERACIONAL):
    estacao = estacao_service.criar_estacao(
        EstacaoCreate(
            nome="Centro",
            endereco="Rua A",
            latitude=-27.6,
            longitude=-48.5,
            capacidade_total=capacidade,
        )
    )
    estacao.status = status
    return estacao


def _cadastrar(estacao_id):
    return service.cadastrar_bicicleta(BicicletaCreate(estacao_id=estacao_id))


class BaseTestCase(unittest.TestCase):
    def setUp(self):
        memoria.estacoes.clear()
        memoria.bicicletas.clear()
        memoria._contadores.clear()

    def codigo_http(self, funcao, *args):
        with self.assertRaises(HTTPException) as ctx:
            funcao(*args)
        return ctx.exception.status_code


class CadastroTests(BaseTestCase):
    def test_cadastra_bicicleta_disponivel_na_estacao_com_qr_gerado(self):
        estacao = _estacao()
        bicicleta = _cadastrar(estacao.id)
        self.assertEqual(bicicleta.estacao_id, estacao.id)
        self.assertEqual(bicicleta.status, StatusBicicleta.DISPONIVEL)
        self.assertFalse(bicicleta.bloqueio_pendente)
        self.assertTrue(bicicleta.qr_code.startswith("BIKE-"))
        self.assertTrue(bicicleta.apta_para_locacao())

    def test_cadastro_ocupa_uma_vaga(self):
        estacao = _estacao(capacidade=3)
        self.assertEqual(estacao_service.vagas_disponiveis(estacao), 3)
        _cadastrar(estacao.id)
        _cadastrar(estacao.id)
        self.assertEqual(estacao_service.vagas_disponiveis(estacao), 1)
        self.assertEqual(estacao_service.to_public(estacao).vagas_disponiveis, 1)

    def test_qr_codes_sao_unicos_e_ids_diferentes(self):
        estacao = _estacao(capacidade=20)
        bicicletas = [_cadastrar(estacao.id) for _ in range(20)]
        self.assertEqual(len({b.qr_code for b in bicicletas}), 20)
        self.assertEqual(len({b.id for b in bicicletas}), 20)

    def test_qr_nao_e_derivado_do_id(self):
        estacao = _estacao(capacidade=2)
        a, b = _cadastrar(estacao.id), _cadastrar(estacao.id)
        self.assertNotEqual(a.qr_code, f"BIKE-{a.id}")
        self.assertNotEqual(b.qr_code, f"BIKE-{b.id}")

    def test_colisao_de_qr_gera_outro_codigo(self):
        # o sorteio devolve o mesmo valor duas vezes; o segundo create tem que sortear de novo
        sorteios = iter(["a" * 32, "a" * 32, "b" * 32])
        with mock.patch.object(
            repo.uuid, "uuid4", side_effect=lambda: SimpleNamespace(hex=next(sorteios))
        ):
            primeira = repo.create(1)
            segunda = repo.create(1)
        self.assertEqual(primeira.qr_code, "BIKE-" + "A" * 12)
        self.assertEqual(segunda.qr_code, "BIKE-" + "B" * 12)

    def test_estacao_inexistente_404(self):
        self.assertEqual(self.codigo_http(_cadastrar, 999), 404)
        self.assertEqual(memoria.bicicletas, {})

    def test_estacao_lotada_409_e_nao_cadastra(self):
        estacao = _estacao(capacidade=2)
        _cadastrar(estacao.id)
        _cadastrar(estacao.id)
        self.assertEqual(self.codigo_http(_cadastrar, estacao.id), 409)
        self.assertEqual(len(repo.list_by_estacao(estacao.id)), 2)
        self.assertEqual(estacao_service.vagas_disponiveis(estacao), 0)

    def test_estacao_bloqueada_ou_em_manutencao_409(self):
        for status in (StatusEstacao.BLOQUEADA, StatusEstacao.EM_MANUTENCAO):
            with self.subTest(status=status):
                estacao = _estacao(status=status)
                self.assertEqual(self.codigo_http(_cadastrar, estacao.id), 409)
                self.assertEqual(repo.list_by_estacao(estacao.id), [])

    def test_schema_recusa_estacao_id_invalido(self):
        for valor in (0, -1, "abc", None):
            with self.subTest(valor=valor):
                with self.assertRaises(ValidationError):
                    BicicletaCreate(estacao_id=valor)


class VagaLivreTests(BaseTestCase):
    def test_possui_vaga_livre(self):
        estacao = _estacao(capacidade=1)
        self.assertTrue(estacao_service.possui_vaga_livre(estacao.id))
        _cadastrar(estacao.id)
        self.assertFalse(estacao_service.possui_vaga_livre(estacao.id))

    def test_possui_vaga_livre_falso_se_nao_operacional(self):
        estacao = _estacao(status=StatusEstacao.BLOQUEADA)
        self.assertFalse(estacao_service.possui_vaga_livre(estacao.id))

    def test_estacao_inexistente_404(self):
        self.assertEqual(self.codigo_http(estacao_service.possui_vaga_livre, 999), 404)
        self.assertEqual(self.codigo_http(estacao_service.exigir_vaga_livre, 999), 404)

    def test_bicicleta_em_manutencao_continua_ocupando_vaga(self):
        estacao = _estacao(capacidade=1)
        bicicleta = _cadastrar(estacao.id)
        service.set_status(bicicleta.id, StatusBicicleta.EM_MANUTENCAO)
        self.assertFalse(estacao_service.possui_vaga_livre(estacao.id))


class QrCodeTests(BaseTestCase):
    def test_get_by_qr_encontra_a_bicicleta(self):
        estacao = _estacao()
        bicicleta = _cadastrar(estacao.id)
        self.assertIs(service.get_by_qr(bicicleta.qr_code), bicicleta)

    def test_get_by_qr_ignora_espacos_e_quebra_de_linha_do_leitor(self):
        bicicleta = _cadastrar(_estacao().id)
        self.assertIs(service.get_by_qr(f"  {bicicleta.qr_code}\n"), bicicleta)

    def test_qr_inexistente_vazio_ou_nulo_da_404(self):
        _cadastrar(_estacao().id)
        for qr in ("BIKE-NAOEXISTE", "", "   ", None):
            with self.subTest(qr=qr):
                self.assertEqual(self.codigo_http(service.get_by_qr, qr), 404)


class StatusTests(BaseTestCase):
    def test_set_status_troca_e_apta_acompanha(self):
        bicicleta = _cadastrar(_estacao().id)
        esperado = {
            StatusBicicleta.DISPONIVEL: True,
            StatusBicicleta.EM_USO: False,
            StatusBicicleta.EM_MANUTENCAO: False,
            StatusBicicleta.BLOQUEADA: False,
        }
        for novo, apta in esperado.items():
            with self.subTest(status=novo):
                service.set_status(bicicleta.id, novo)
                self.assertEqual(repo.get_by_id(bicicleta.id).status, novo)
                self.assertEqual(bicicleta.apta_para_locacao(), apta)

    def test_set_status_bicicleta_inexistente_404(self):
        self.assertEqual(
            self.codigo_http(service.set_status, 999, StatusBicicleta.BLOQUEADA), 404
        )

    def test_set_status_valor_invalido_nao_altera(self):
        bicicleta = _cadastrar(_estacao().id)
        with self.assertRaises(ValueError):
            service.set_status(bicicleta.id, "VOANDO")
        self.assertEqual(bicicleta.status, StatusBicicleta.DISPONIVEL)


class ListagemTests(BaseTestCase):
    def test_filtros_por_status_e_estacao(self):
        e1, e2 = _estacao(capacidade=5), _estacao(capacidade=5)
        a, b, c = _cadastrar(e1.id), _cadastrar(e1.id), _cadastrar(e2.id)
        service.set_status(b.id, StatusBicicleta.EM_MANUTENCAO)

        ids = lambda lista: sorted(x.id for x in lista)
        self.assertEqual(ids(service.listar_bicicletas()), sorted([a.id, b.id, c.id]))
        self.assertEqual(ids(service.listar_bicicletas(estacao_id=e1.id)), sorted([a.id, b.id]))
        self.assertEqual(ids(service.listar_bicicletas(status=StatusBicicleta.EM_MANUTENCAO)), [b.id])
        self.assertEqual(
            ids(service.listar_bicicletas(StatusBicicleta.DISPONIVEL, e1.id)), [a.id]
        )
        self.assertEqual(service.listar_bicicletas(estacao_id=999), [])


if __name__ == "__main__":
    unittest.main()
