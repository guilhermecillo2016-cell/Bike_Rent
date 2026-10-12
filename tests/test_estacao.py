"""
tests/test_estacao.py
-----------------------
Testes da A4: ocupação das estações (alocar e remover bicicleta) e os
campos status e bicicletas_disponiveis do EstacaoPublic.

Rodar da raiz do projeto:
    python -m unittest discover -s tests -t . -v
"""

import unittest

from fastapi import HTTPException

from dominio.estacao import service
from dominio.estacao.schemas import EstacaoCreate
from servicos_tecnicos.banco_de_dados import memoria
from servicos_tecnicos.banco_de_dados import repository_bicicleta as repo
from servicos_tecnicos.banco_de_dados.enums import StatusBicicleta, StatusEstacao


def _estacao(capacidade=3, status=StatusEstacao.OPERACIONAL):
    estacao = service.criar_estacao(
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


def _bicicleta_solta():
    """Bicicleta que não está em nenhuma estação (como numa corrida)."""
    bicicleta = repo.create(estacao_id=None)
    return bicicleta


class BaseTestCase(unittest.TestCase):
    def setUp(self):
        memoria.estacoes.clear()
        memoria.bicicletas.clear()
        memoria._contadores.clear()

    def codigo_http(self, funcao, *args):
        with self.assertRaises(HTTPException) as ctx:
            funcao(*args)
        return ctx.exception.status_code


class AlocarTests(BaseTestCase):
    def test_estaciona_a_bicicleta_e_ocupa_uma_vaga(self):
        estacao = _estacao(capacidade=3)
        bicicleta = _bicicleta_solta()
        resultado = service.alocar_bicicleta(estacao.id, bicicleta.id)
        self.assertIs(resultado, bicicleta)
        self.assertEqual(bicicleta.estacao_id, estacao.id)
        self.assertEqual(service.vagas_disponiveis(estacao), 2)

    def test_estacao_inexistente_404(self):
        bicicleta = _bicicleta_solta()
        self.assertEqual(self.codigo_http(service.alocar_bicicleta, 999, bicicleta.id), 404)
        self.assertIsNone(bicicleta.estacao_id)

    def test_bicicleta_inexistente_404(self):
        estacao = _estacao()
        self.assertEqual(self.codigo_http(service.alocar_bicicleta, estacao.id, 999), 404)
        self.assertEqual(service.vagas_disponiveis(estacao), 3)

    def test_estacao_lotada_409_e_nao_move_a_bicicleta(self):
        estacao = _estacao(capacidade=1)
        service.alocar_bicicleta(estacao.id, _bicicleta_solta().id)
        outra = _bicicleta_solta()
        self.assertEqual(self.codigo_http(service.alocar_bicicleta, estacao.id, outra.id), 409)
        self.assertIsNone(outra.estacao_id)
        self.assertEqual(service.vagas_disponiveis(estacao), 0)

    def test_estacao_bloqueada_ou_em_manutencao_409(self):
        for status in (StatusEstacao.BLOQUEADA, StatusEstacao.EM_MANUTENCAO):
            with self.subTest(status=status):
                estacao = _estacao(status=status)
                bicicleta = _bicicleta_solta()
                self.assertEqual(
                    self.codigo_http(service.alocar_bicicleta, estacao.id, bicicleta.id), 409
                )
                self.assertIsNone(bicicleta.estacao_id)

    def test_bicicleta_que_ja_esta_numa_estacao_409(self):
        a, b = _estacao(), _estacao()
        bicicleta = _bicicleta_solta()
        service.alocar_bicicleta(a.id, bicicleta.id)
        self.assertEqual(self.codigo_http(service.alocar_bicicleta, b.id, bicicleta.id), 409)
        self.assertEqual(bicicleta.estacao_id, a.id)
        self.assertEqual(service.vagas_disponiveis(a), 2)
        self.assertEqual(service.vagas_disponiveis(b), 3)

    def test_ocupacao_nunca_passa_da_capacidade(self):
        estacao = _estacao(capacidade=2)
        aceitas = 0
        for _ in range(5):
            try:
                service.alocar_bicicleta(estacao.id, _bicicleta_solta().id)
                aceitas += 1
            except HTTPException:
                pass
        self.assertEqual(aceitas, 2)
        self.assertEqual(len(repo.list_by_estacao(estacao.id)), 2)
        self.assertEqual(service.vagas_disponiveis(estacao), 0)


class RemoverTests(BaseTestCase):
    def test_libera_a_vaga_e_deixa_a_bicicleta_solta(self):
        estacao = _estacao(capacidade=2)
        bicicleta = _bicicleta_solta()
        service.alocar_bicicleta(estacao.id, bicicleta.id)
        resultado = service.remover_bicicleta(bicicleta.id)
        self.assertIs(resultado, bicicleta)
        self.assertIsNone(bicicleta.estacao_id)
        self.assertEqual(service.vagas_disponiveis(estacao), 2)

    def test_bicicleta_inexistente_404(self):
        self.assertEqual(self.codigo_http(service.remover_bicicleta, 999), 404)

    def test_bicicleta_que_nao_esta_em_estacao_409(self):
        bicicleta = _bicicleta_solta()
        self.assertEqual(self.codigo_http(service.remover_bicicleta, bicicleta.id), 409)

    def test_estacao_bloqueada_ou_em_manutencao_nao_libera_409(self):
        for status in (StatusEstacao.BLOQUEADA, StatusEstacao.EM_MANUTENCAO):
            with self.subTest(status=status):
                estacao = _estacao()
                bicicleta = _bicicleta_solta()
                service.alocar_bicicleta(estacao.id, bicicleta.id)
                estacao.status = status
                self.assertEqual(self.codigo_http(service.remover_bicicleta, bicicleta.id), 409)
                self.assertEqual(bicicleta.estacao_id, estacao.id)

    def test_remover_e_alocar_em_outra_estacao_move_a_bicicleta(self):
        origem, destino = _estacao(capacidade=2), _estacao(capacidade=2)
        bicicleta = _bicicleta_solta()
        service.alocar_bicicleta(origem.id, bicicleta.id)
        service.remover_bicicleta(bicicleta.id)
        service.alocar_bicicleta(destino.id, bicicleta.id)
        self.assertEqual(bicicleta.estacao_id, destino.id)
        self.assertEqual(service.vagas_disponiveis(origem), 2)
        self.assertEqual(service.vagas_disponiveis(destino), 1)


class EstacaoPublicTests(BaseTestCase):
    def test_estacao_vazia_mostra_status_e_zero_bicicletas(self):
        publico = service.to_public(_estacao(capacidade=5))
        self.assertEqual(publico.status, StatusEstacao.OPERACIONAL)
        self.assertEqual(publico.vagas_disponiveis, 5)
        self.assertEqual(publico.bicicletas_disponiveis, 0)

    def test_so_conta_como_disponivel_a_bicicleta_alugavel(self):
        estacao = _estacao(capacidade=5)
        ids = []
        for _ in range(3):
            bicicleta = _bicicleta_solta()
            service.alocar_bicicleta(estacao.id, bicicleta.id)
            ids.append(bicicleta.id)
        repo.get_by_id(ids[1]).status = StatusBicicleta.EM_MANUTENCAO
        repo.get_by_id(ids[2]).status = StatusBicicleta.BLOQUEADA

        publico = service.to_public(estacao)
        self.assertEqual(publico.bicicletas_disponiveis, 1)
        # as três continuam ocupando vaga, mesmo as que não podem ser alugadas
        self.assertEqual(publico.vagas_disponiveis, 2)

    def test_status_da_estacao_aparece_no_publico(self):
        for status in StatusEstacao:
            with self.subTest(status=status):
                self.assertEqual(service.to_public(_estacao(status=status)).status, status)

    def test_bicicleta_em_uso_nao_conta_na_estacao(self):
        estacao = _estacao(capacidade=2)
        bicicleta = _bicicleta_solta()
        service.alocar_bicicleta(estacao.id, bicicleta.id)
        service.remover_bicicleta(bicicleta.id)
        bicicleta.status = StatusBicicleta.EM_USO
        publico = service.to_public(estacao)
        self.assertEqual(publico.bicicletas_disponiveis, 0)
        self.assertEqual(publico.vagas_disponiveis, 2)


if __name__ == "__main__":
    unittest.main()
