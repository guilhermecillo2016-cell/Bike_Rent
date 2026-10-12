"""
tests/test_status_manual.py
-----------------------------
Testes da A5 (UC2, gerenciar frota): alteração manual de status de
bicicleta e estação, com auditoria, e a regra da bicicleta em corrida.

Rodar da raiz do projeto:
    python -m unittest discover -s tests -t . -v
"""

import unittest

from fastapi import HTTPException

from apresentacao import adminweb
from dominio.auditoria import service as auditoria
from dominio.bicicleta import service as bicicletas
from dominio.bicicleta.schemas import BicicletaCreate
from dominio.estacao import service as estacoes
from dominio.estacao.schemas import EstacaoCreate
from servicos_tecnicos.banco_de_dados import memoria
from servicos_tecnicos.banco_de_dados import repository_avaria
from servicos_tecnicos.banco_de_dados.enums import (
    StatusAvaria,
    StatusBicicleta,
    StatusEstacao,
)

OP = "olga@x.com"


def _estacao(capacidade=3):
    return estacoes.criar_estacao(
        EstacaoCreate(
            nome="Centro",
            endereco="Rua A",
            latitude=-27.6,
            longitude=-48.5,
            capacidade_total=capacidade,
        )
    )


def _bicicleta(estacao):
    return bicicletas.cadastrar_bicicleta(BicicletaCreate(estacao_id=estacao.id))


def _em_corrida(estacao):
    """Bicicleta na rua, como a locação deixa: sem estação e EM_USO."""
    bicicleta = _bicicleta(estacao)
    estacoes.remover_bicicleta(bicicleta.id)
    bicicletas.set_status(bicicleta.id, StatusBicicleta.EM_USO)
    return bicicleta


class BaseTestCase(unittest.TestCase):
    def setUp(self):
        for colecao in (memoria.estacoes, memoria.bicicletas, memoria.avarias, memoria.eventos_auditoria):
            colecao.clear()
        memoria._contadores.clear()

    def codigo_http(self, funcao, *args):
        with self.assertRaises(HTTPException) as ctx:
            funcao(*args)
        return ctx.exception.status_code


class BicicletaManualTests(BaseTestCase):
    def test_troca_o_status_e_registra_um_evento(self):
        bicicleta = _bicicleta(_estacao())
        resultado = bicicletas.alterar_status_manual(bicicleta.id, StatusBicicleta.EM_MANUTENCAO, OP)
        self.assertIs(resultado, bicicleta)
        self.assertEqual(bicicleta.status, StatusBicicleta.EM_MANUTENCAO)

        eventos = auditoria.listar()
        self.assertEqual(len(eventos), 1)
        evento = eventos[0]
        self.assertEqual(
            (evento.usuario_email, evento.tipo_entidade, evento.entidade_id,
             evento.status_anterior, evento.status_novo),
            (OP, "BICICLETA", bicicleta.id, "DISPONIVEL", "EM_MANUTENCAO"),
        )
        self.assertIsNotNone(evento.data_hora)

    def test_bloquear_e_depois_liberar(self):
        bicicleta = _bicicleta(_estacao())
        bicicletas.alterar_status_manual(bicicleta.id, StatusBicicleta.BLOQUEADA, OP)
        self.assertFalse(bicicleta.apta_para_locacao())
        bicicletas.alterar_status_manual(bicicleta.id, StatusBicicleta.DISPONIVEL, OP)
        self.assertTrue(bicicleta.apta_para_locacao())
        self.assertEqual(len(auditoria.listar()), 2)

    def test_mesmo_status_nao_registra_evento(self):
        bicicleta = _bicicleta(_estacao())
        bicicletas.alterar_status_manual(bicicleta.id, StatusBicicleta.DISPONIVEL, OP)
        self.assertEqual(auditoria.listar(), [])

    def test_bicicleta_inexistente_404(self):
        self.assertEqual(
            self.codigo_http(bicicletas.alterar_status_manual, 999, StatusBicicleta.BLOQUEADA, OP), 404
        )
        self.assertEqual(auditoria.listar(), [])

    def test_nao_se_marca_em_uso_a_mao_400(self):
        bicicleta = _bicicleta(_estacao())
        self.assertEqual(
            self.codigo_http(bicicletas.alterar_status_manual, bicicleta.id, StatusBicicleta.EM_USO, OP), 400
        )
        self.assertEqual(bicicleta.status, StatusBicicleta.DISPONIVEL)
        self.assertEqual(auditoria.listar(), [])

    def test_status_invalido_nao_altera_nada(self):
        bicicleta = _bicicleta(_estacao())
        with self.assertRaises(ValueError):
            bicicletas.alterar_status_manual(bicicleta.id, "VOANDO", OP)
        self.assertEqual(bicicleta.status, StatusBicicleta.DISPONIVEL)
        self.assertEqual(auditoria.listar(), [])


class BicicletaEmCorridaTests(BaseTestCase):
    def test_bloquear_em_corrida_so_agenda(self):
        for pedido in (StatusBicicleta.BLOQUEADA, StatusBicicleta.EM_MANUTENCAO):
            with self.subTest(pedido=pedido):
                memoria.eventos_auditoria.clear()
                bicicleta = _em_corrida(_estacao())
                bicicletas.alterar_status_manual(bicicleta.id, pedido, OP)
                self.assertEqual(bicicleta.status, StatusBicicleta.EM_USO)
                self.assertTrue(bicicleta.bloqueio_pendente)
                eventos = auditoria.listar()
                self.assertEqual(len(eventos), 1)
                self.assertEqual(eventos[0].status_anterior, "EM_USO")
                self.assertEqual(eventos[0].status_novo, "EM_MANUTENCAO (agendado)")

    def test_pedir_de_novo_nao_duplica_o_evento(self):
        bicicleta = _em_corrida(_estacao())
        bicicletas.alterar_status_manual(bicicleta.id, StatusBicicleta.BLOQUEADA, OP)
        bicicletas.alterar_status_manual(bicicleta.id, StatusBicicleta.EM_MANUTENCAO, OP)
        self.assertEqual(len(auditoria.listar()), 1)

    def test_liberar_bicicleta_em_corrida_409(self):
        bicicleta = _em_corrida(_estacao())
        self.assertEqual(
            self.codigo_http(bicicletas.alterar_status_manual, bicicleta.id, StatusBicicleta.DISPONIVEL, OP), 409
        )
        self.assertEqual(bicicleta.status, StatusBicicleta.EM_USO)
        self.assertFalse(bicicleta.bloqueio_pendente)

    def test_fim_da_corrida_com_bloqueio_agendado_vai_para_manutencao(self):
        bicicleta = _em_corrida(_estacao())
        bicicletas.alterar_status_manual(bicicleta.id, StatusBicicleta.BLOQUEADA, OP)
        bicicletas.finalizar_uso(bicicleta.id)
        self.assertEqual(bicicleta.status, StatusBicicleta.EM_MANUTENCAO)
        self.assertFalse(bicicleta.bloqueio_pendente)
        ultimo = auditoria.listar()[0]
        self.assertEqual(ultimo.usuario_email, "sistema")
        self.assertEqual((ultimo.status_anterior, ultimo.status_novo), ("EM_USO", "EM_MANUTENCAO"))

    def test_fim_da_corrida_sem_bloqueio_volta_a_disponivel_sem_evento(self):
        bicicleta = _em_corrida(_estacao())
        bicicletas.finalizar_uso(bicicleta.id)
        self.assertEqual(bicicleta.status, StatusBicicleta.DISPONIVEL)
        self.assertEqual(auditoria.listar(), [])

    def test_finalizar_uso_de_bicicleta_inexistente_404(self):
        self.assertEqual(self.codigo_http(bicicletas.finalizar_uso, 999), 404)


class AvariaPendenteTests(BaseTestCase):
    def _bloqueada_com_avaria(self, status_avaria):
        bicicleta = _bicicleta(_estacao())
        bicicletas.alterar_status_manual(bicicleta.id, StatusBicicleta.EM_MANUTENCAO, OP)
        avaria = repository_avaria.create("pneu furado", "cid@x.com", bicicleta.id)
        avaria.status = status_avaria
        return bicicleta

    def test_liberar_com_avaria_pendente_ou_em_reparo_409(self):
        for status in (StatusAvaria.PENDENTE, StatusAvaria.EM_REPARO):
            with self.subTest(status=status):
                bicicleta = self._bloqueada_com_avaria(status)
                self.assertEqual(
                    self.codigo_http(bicicletas.alterar_status_manual, bicicleta.id, StatusBicicleta.DISPONIVEL, OP), 409
                )
                self.assertEqual(bicicleta.status, StatusBicicleta.EM_MANUTENCAO)

    def test_liberar_com_avaria_resolvida_pode(self):
        bicicleta = self._bloqueada_com_avaria(StatusAvaria.RESOLVIDO)
        bicicletas.alterar_status_manual(bicicleta.id, StatusBicicleta.DISPONIVEL, OP)
        self.assertEqual(bicicleta.status, StatusBicicleta.DISPONIVEL)

    def test_avaria_pendente_nao_impede_bloquear(self):
        bicicleta = _bicicleta(_estacao())
        repository_avaria.create("freio", "cid@x.com", bicicleta.id)
        bicicletas.alterar_status_manual(bicicleta.id, StatusBicicleta.BLOQUEADA, OP)
        self.assertEqual(bicicleta.status, StatusBicicleta.BLOQUEADA)

    def test_avaria_de_outra_bicicleta_nao_atrapalha(self):
        estacao = _estacao()
        a, b = _bicicleta(estacao), _bicicleta(estacao)
        repository_avaria.create("freio", "cid@x.com", a.id)
        bicicletas.alterar_status_manual(b.id, StatusBicicleta.BLOQUEADA, OP)
        bicicletas.alterar_status_manual(b.id, StatusBicicleta.DISPONIVEL, OP)
        self.assertEqual(b.status, StatusBicicleta.DISPONIVEL)


class EstacaoManualTests(BaseTestCase):
    def test_troca_o_status_e_registra_um_evento(self):
        estacao = _estacao()
        estacoes.alterar_status_manual(estacao.id, StatusEstacao.BLOQUEADA, OP)
        self.assertEqual(estacao.status, StatusEstacao.BLOQUEADA)
        evento = auditoria.listar()[0]
        self.assertEqual(
            (evento.usuario_email, evento.tipo_entidade, evento.entidade_id,
             evento.status_anterior, evento.status_novo),
            (OP, "ESTACAO", estacao.id, "OPERACIONAL", "BLOQUEADA"),
        )

    def test_todos_os_status_sao_aceitos(self):
        estacao = _estacao()
        for status in (StatusEstacao.BLOQUEADA, StatusEstacao.EM_MANUTENCAO, StatusEstacao.OPERACIONAL):
            estacoes.alterar_status_manual(estacao.id, status, OP)
            self.assertEqual(estacao.status, status)
        self.assertEqual(len(auditoria.listar()), 3)

    def test_mesmo_status_nao_registra_evento(self):
        estacao = _estacao()
        estacoes.alterar_status_manual(estacao.id, StatusEstacao.OPERACIONAL, OP)
        self.assertEqual(auditoria.listar(), [])

    def test_estacao_inexistente_404(self):
        self.assertEqual(
            self.codigo_http(estacoes.alterar_status_manual, 999, StatusEstacao.BLOQUEADA, OP), 404
        )

    def test_estacao_bloqueada_trava_retirada_e_devolucao(self):
        estacao = _estacao()
        bicicleta = _bicicleta(estacao)
        estacoes.alterar_status_manual(estacao.id, StatusEstacao.BLOQUEADA, OP)
        self.assertEqual(self.codigo_http(estacoes.remover_bicicleta, bicicleta.id), 409)
        self.assertEqual(self.codigo_http(bicicletas.cadastrar_bicicleta, BicicletaCreate(estacao_id=estacao.id)), 409)

    def test_status_aparece_no_estacao_public(self):
        estacao = _estacao()
        estacoes.alterar_status_manual(estacao.id, StatusEstacao.EM_MANUTENCAO, OP)
        self.assertEqual(estacoes.to_public(estacao).status, StatusEstacao.EM_MANUTENCAO)


class AuditoriaTests(BaseTestCase):
    def test_listar_do_mais_recente_para_o_mais_antigo(self):
        for i in range(3):
            auditoria.registrar(OP, "ESTACAO", i + 1, "OPERACIONAL", "BLOQUEADA")
        self.assertEqual([e.entidade_id for e in auditoria.listar()], [3, 2, 1])

    def test_listar_vazio(self):
        self.assertEqual(auditoria.listar(), [])

    def test_to_public_leva_todos_os_campos(self):
        evento = auditoria.registrar(OP, "BICICLETA", 7, "DISPONIVEL", "BLOQUEADA")
        publico = auditoria.to_public(evento)
        self.assertEqual(
            (publico.id, publico.usuario_email, publico.tipo_entidade, publico.entidade_id,
             publico.status_anterior, publico.status_novo, publico.data_hora),
            (evento.id, OP, "BICICLETA", 7, "DISPONIVEL", "BLOQUEADA", evento.data_hora),
        )


class RotasTests(unittest.TestCase):
    """Sem servidor: confere qual papel cada rota exige."""

    def _dependencias(self, caminho, metodo):
        for rota in adminweb.router.routes:
            if rota.path == caminho and metodo in rota.methods:
                return [d.call for d in rota.dependant.dependencies]
        self.fail(f"rota {metodo} {caminho} não encontrada")

    def test_status_de_bicicleta_e_estacao_sao_para_a_equipe(self):
        for caminho in ("/adminweb/bicicletas/{bicicleta_id}/status", "/adminweb/estacoes/{estacao_id}/status"):
            with self.subTest(caminho=caminho):
                self.assertIn(adminweb.equipe, self._dependencias(caminho, "PATCH"))
                self.assertNotIn(adminweb.somente_admin, self._dependencias(caminho, "PATCH"))

    def test_auditoria_so_para_administrador(self):
        self.assertIn(adminweb.somente_admin, self._dependencias("/adminweb/auditoria", "GET"))


if __name__ == "__main__":
    unittest.main()
