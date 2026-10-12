"""
tests/test_relatorio.py
-------------------------
Testes da A6 (UC3, relatório analítico). Os dados são montados à mão e
as contas esperadas estão no comentário de cada teste.

Rodar da raiz do projeto:
    python -m unittest discover -s tests -t . -v

Cenário (estação A = 1 com b1, b2, b3; estação B = 2 com b4):

  locação  bicicleta  origem  início             pagamento
  L1       b1         A       01/10 08:10        4,00 aprovado
  L2       b1         A       01/10 08:40        6,00 aprovado
  L3       b2         A       01/10 17:05        2,00 aprovado
  L4       b4         B       02/10 17:30        10,00 RECUSADO
  L5       b4         B       02/10 17:45        5,00 aprovado
  L6       b4         B       03/10 09:00        3,00 aprovado
  L7       b3         A       15/09 12:00        8,00 aprovado   (fora de outubro)
  pacote   -          -       02/10 10:00        30,00 aprovado

  avarias: b1 em 01/10 e 02/10, b4 em 03/10, b3 em 10/09 (fora de outubro)
"""

import unittest
from datetime import date, datetime

from fastapi import HTTPException

from apresentacao import adminweb
from dominio.relatorio import service
from servicos_tecnicos.banco_de_dados import memoria
from servicos_tecnicos.banco_de_dados import repository_avaria
from servicos_tecnicos.banco_de_dados import repository_bicicleta
from servicos_tecnicos.banco_de_dados import repository_estacao
from servicos_tecnicos.banco_de_dados import repository_locacao
from servicos_tecnicos.banco_de_dados import repository_pagamento
from servicos_tecnicos.banco_de_dados.enums import StatusPagamento, TipoPagamento

A, B = 1, 2


def _montar():
    repository_estacao.create("Centro", "Rua A", -27.6, -48.5, 10)
    repository_estacao.create("Praia", "Rua B", -27.5, -48.4, 10)
    for estacao in (A, A, A, B):
        repository_bicicleta.create(estacao)  # b1, b2, b3, b4

    def locacao(bicicleta, origem, quando, valor, status, pago_em):
        l = repository_locacao.create("cid@x.com", bicicleta, origem)
        l.data_hora_inicio = quando
        l.valor_total = valor
        l.em_andamento = False
        p = repository_pagamento.create(valor, TipoPagamento.CARTAO_CREDITO, locacao_id=l.id)
        p.status = status
        p.data_hora = pago_em

    aprovado, recusado = StatusPagamento.APROVADO, StatusPagamento.RECUSADO
    locacao(1, A, datetime(2026, 10, 1, 8, 10), 4.0, aprovado, datetime(2026, 10, 1, 8, 50))
    locacao(1, A, datetime(2026, 10, 1, 8, 40), 6.0, aprovado, datetime(2026, 10, 1, 9, 10))
    locacao(2, A, datetime(2026, 10, 1, 17, 5), 2.0, aprovado, datetime(2026, 10, 1, 17, 30))
    locacao(4, B, datetime(2026, 10, 2, 17, 30), 10.0, recusado, datetime(2026, 10, 2, 17, 50))
    locacao(4, B, datetime(2026, 10, 2, 17, 45), 5.0, aprovado, datetime(2026, 10, 2, 18, 0))
    locacao(4, B, datetime(2026, 10, 3, 9, 0), 3.0, aprovado, datetime(2026, 10, 3, 9, 20))
    locacao(3, A, datetime(2026, 9, 15, 12, 0), 8.0, aprovado, datetime(2026, 9, 15, 12, 30))

    pacote = repository_pagamento.create(30.0, TipoPagamento.CARTAO_CREDITO, pacote_id=1)
    pacote.status = aprovado
    pacote.data_hora = datetime(2026, 10, 2, 10, 0)

    for bicicleta, quando in ((1, datetime(2026, 10, 1, 18, 0)), (1, datetime(2026, 10, 2, 8, 0)),
                              (4, datetime(2026, 10, 3, 9, 30)), (3, datetime(2026, 9, 10, 10, 0))):
        repository_avaria.create("defeito", "cid@x.com", bicicleta).data_hora = quando


OUTUBRO = dict(inicio=date(2026, 10, 1), fim=date(2026, 10, 3))


class RelatorioTestCase(unittest.TestCase):
    def setUp(self):
        for colecao in (memoria.estacoes, memoria.bicicletas, memoria.locacoes,
                        memoria.pagamentos, memoria.avarias):
            colecao.clear()
        memoria._contadores.clear()

    def codigo_http(self, **filtros):
        with self.assertRaises(HTTPException) as ctx:
            service.gerar_relatorio(**filtros)
        return ctx.exception.status_code


class SemDadosTests(RelatorioTestCase):
    def test_sistema_vazio_devolve_zeros_e_nao_erro(self):
        r = service.gerar_relatorio()
        self.assertEqual(
            (r.receita_total, r.receita_corridas, r.receita_pacotes, r.total_locacoes,
             r.bicicletas_total, r.bicicletas_ociosas, r.taxa_ociosidade,
             r.total_avarias, r.indice_quebras),
            (0.0, 0.0, 0.0, 0, 0, 0, 0.0, 0, 0.0),
        )
        self.assertEqual(r.horarios_pico, [])
        self.assertIsInstance(r.data_geracao, datetime)

    def test_periodo_sem_nenhum_dado_devolve_zeros(self):
        _montar()
        r = service.gerar_relatorio(inicio=date(2030, 1, 1), fim=date(2030, 1, 31))
        self.assertEqual((r.receita_total, r.total_locacoes, r.total_avarias, r.indice_quebras), (0.0, 0, 0, 0.0))
        self.assertEqual(r.horarios_pico, [])
        # a frota existe e ninguém andou: tudo ocioso
        self.assertEqual((r.bicicletas_total, r.bicicletas_ociosas, r.taxa_ociosidade), (4, 4, 1.0))

    def test_estacao_sem_corridas(self):
        repository_estacao.create("Vazia", "Rua C", 0, 0, 5)
        r = service.gerar_relatorio(estacao_id=1)
        self.assertEqual((r.total_locacoes, r.receita_total, r.bicicletas_total, r.taxa_ociosidade), (0, 0.0, 0, 0.0))


class PeriodoTodoTests(RelatorioTestCase):
    def test_outubro_inteiro_sem_filtro_de_estacao(self):
        _montar()
        r = service.gerar_relatorio(**OUTUBRO)
        # receita: corridas 4+6+2+5+3 = 20 (a de 10,00 foi recusada); pacote 30
        self.assertEqual((r.receita_corridas, r.receita_pacotes, r.receita_total), (20.0, 30.0, 50.0))
        self.assertEqual(r.total_locacoes, 6)
        # b3 foi a única que não andou em outubro: 1 de 4
        self.assertEqual((r.bicicletas_total, r.bicicletas_ociosas, r.taxa_ociosidade), (4, 1, 0.25))
        # 3 avarias em outubro / 6 corridas
        self.assertEqual((r.total_avarias, r.indice_quebras), (3, 0.5))

    def test_horario_de_pico_por_estacao(self):
        _montar()
        a, b = service.gerar_relatorio(**OUTUBRO).horarios_pico
        # A: 8h (L1, L2) e 17h (L3) -> pico 8h com 2
        self.assertEqual((a.estacao_id, a.estacao_nome, a.total_locacoes, a.hora_pico, a.locacoes_na_hora_pico),
                         (A, "Centro", 3, 8, 2))
        # B: 17h (L4, L5) e 9h (L6) -> pico 17h com 2
        self.assertEqual((b.estacao_id, b.estacao_nome, b.total_locacoes, b.hora_pico, b.locacoes_na_hora_pico),
                         (B, "Praia", 3, 17, 2))

    def test_sem_nenhum_filtro_conta_tudo(self):
        _montar()
        r = service.gerar_relatorio()
        # corridas 28 (inclui os 8,00 de setembro); pacote 30
        self.assertEqual((r.receita_corridas, r.receita_pacotes, r.receita_total), (28.0, 30.0, 58.0))
        self.assertEqual(r.total_locacoes, 7)
        self.assertEqual((r.bicicletas_ociosas, r.taxa_ociosidade), (0, 0.0))
        self.assertEqual((r.total_avarias, r.indice_quebras), (4, round(4 / 7, 4)))

    def test_pagamento_recusado_nao_entra_na_receita(self):
        _montar()
        r = service.gerar_relatorio(inicio=date(2026, 10, 2), fim=date(2026, 10, 2))
        self.assertEqual(r.receita_corridas, 5.0)  # só a de 5,00; a de 10,00 foi recusada
        self.assertEqual(r.receita_pacotes, 30.0)


class FiltroDePeriodoTests(RelatorioTestCase):
    def test_um_unico_dia_inclui_o_dia_inteiro(self):
        _montar()
        dia = date(2026, 10, 1)
        r = service.gerar_relatorio(inicio=dia, fim=dia)
        self.assertEqual(r.total_locacoes, 3)  # 08:10, 08:40 e 17:05
        self.assertEqual(r.receita_total, 12.0)
        self.assertEqual((r.total_avarias, r.indice_quebras), (1, round(1 / 3, 4)))

    def test_so_inicio(self):
        _montar()
        r = service.gerar_relatorio(inicio=date(2026, 10, 2))
        self.assertEqual(r.total_locacoes, 3)
        self.assertEqual((r.receita_corridas, r.receita_pacotes), (8.0, 30.0))

    def test_so_fim(self):
        _montar()
        r = service.gerar_relatorio(fim=date(2026, 9, 30))
        self.assertEqual(r.total_locacoes, 1)
        self.assertEqual(r.receita_total, 8.0)
        self.assertEqual((r.total_avarias, r.indice_quebras), (1, 1.0))
        self.assertEqual((r.bicicletas_ociosas, r.taxa_ociosidade), (3, 0.75))

    def test_inicio_depois_do_fim_400(self):
        self.assertEqual(self.codigo_http(inicio=date(2026, 10, 5), fim=date(2026, 10, 1)), 400)


class FiltroDeEstacaoTests(RelatorioTestCase):
    def test_estacao_a(self):
        _montar()
        r = service.gerar_relatorio(estacao_id=A, **OUTUBRO)
        self.assertEqual(r.estacao_id, A)
        self.assertEqual(r.total_locacoes, 3)
        self.assertEqual((r.receita_corridas, r.receita_pacotes, r.receita_total), (12.0, 0.0, 12.0))
        # frota = b1, b2, b3 (as que estão na estação); b3 não andou
        self.assertEqual((r.bicicletas_total, r.bicicletas_ociosas, r.taxa_ociosidade), (3, 1, round(1 / 3, 4)))
        # avarias de b1 (2) de 3 corridas
        self.assertEqual((r.total_avarias, r.indice_quebras), (2, round(2 / 3, 4)))
        self.assertEqual([p.estacao_id for p in r.horarios_pico], [A])

    def test_estacao_b(self):
        _montar()
        r = service.gerar_relatorio(estacao_id=B, **OUTUBRO)
        self.assertEqual(r.total_locacoes, 3)
        self.assertEqual((r.receita_corridas, r.receita_pacotes), (8.0, 0.0))  # 5 + 3; a de 10 foi recusada
        self.assertEqual((r.bicicletas_total, r.bicicletas_ociosas, r.taxa_ociosidade), (1, 0, 0.0))
        self.assertEqual((r.total_avarias, r.indice_quebras), (1, round(1 / 3, 4)))
        self.assertEqual([p.estacao_id for p in r.horarios_pico], [B])

    def test_pacote_nao_pertence_a_nenhuma_estacao(self):
        _montar()
        for estacao in (A, B):
            self.assertEqual(service.gerar_relatorio(estacao_id=estacao, **OUTUBRO).receita_pacotes, 0.0)

    def test_estacao_inexistente_404(self):
        self.assertEqual(self.codigo_http(estacao_id=999), 404)

    def test_empate_no_pico_fica_com_a_hora_mais_cedo(self):
        repository_estacao.create("Centro", "Rua A", 0, 0, 5)
        repository_bicicleta.create(1)
        for hora in (18, 7):
            repository_locacao.create("cid@x.com", 1, 1).data_hora_inicio = datetime(2026, 10, 1, hora, 0)
        pico = service.gerar_relatorio().horarios_pico[0]
        self.assertEqual((pico.hora_pico, pico.locacoes_na_hora_pico), (7, 1))


class RotaTests(unittest.TestCase):
    def test_relatorios_so_para_administrador(self):
        rota = next(r for r in adminweb.router.routes if r.path == "/adminweb/relatorios")
        dependencias = [d.call for d in rota.dependant.dependencies]
        self.assertIn(adminweb.somente_admin, dependencias)
        self.assertNotIn(adminweb.equipe, dependencias)


if __name__ == "__main__":
    unittest.main()
