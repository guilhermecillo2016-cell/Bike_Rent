"""
tests/test_repositorios.py
----------------------------
Repositórios como classes ([A13]): uma interface (ABC) por repositório, a
implementação em memória, a fábrica, a fachada de módulo e o salvar()
chamado pelos services depois de alterar um objeto.
"""

import ast
import dataclasses
import inspect
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from dominio.bicicleta import service as bicicleta_service
from dominio.estacao import service as estacao_service
from dominio.pacote.service import PacoteService
from dominio.pagamento.pagamento import Pagamento
from dominio.pagamento.service import PagamentoService
from dominio.usuario.usuario import Usuario
from servicos_tecnicos.banco_de_dados import (
    fabrica,
    memoria,
    repositorios,
    repository_auditoria,
    repository_avaria,
    repository_bicicleta,
    repository_cartao,
    repository_comprovante,
    repository_estacao,
    repository_locacao,
    repository_pacote,
    repository_pagamento,
    repository_usuario,
)
from servicos_tecnicos.banco_de_dados.enums import (
    StatusBicicleta,
    StatusEstacao,
    StatusPagamento,
    TipoPagamento,
)
from dominio.pagamento.cartao import Cartao

RAIZ = Path(__file__).resolve().parent.parent
EMAIL = "ana@exemplo.com"

# interface -> (implementação em memória, módulo da fachada, campo na fábrica)
PARES = [
    (repositorios.RepositorioUsuario, repository_usuario, "usuario"),
    (repositorios.RepositorioEstacao, repository_estacao, "estacao"),
    (repositorios.RepositorioBicicleta, repository_bicicleta, "bicicleta"),
    (repositorios.RepositorioLocacao, repository_locacao, "locacao"),
    (repositorios.RepositorioPacote, repository_pacote, "pacote"),
    (repositorios.RepositorioPagamento, repository_pagamento, "pagamento"),
    (repositorios.RepositorioCartao, repository_cartao, "cartao"),
    (repositorios.RepositorioAvaria, repository_avaria, "avaria"),
    (repositorios.RepositorioComprovante, repository_comprovante, "comprovante"),
    (repositorios.RepositorioAuditoria, repository_auditoria, "auditoria"),
]


@pytest.fixture(autouse=True)
def _memoria_limpa():
    colecoes = (
        memoria.usuarios, memoria.estacoes, memoria.bicicletas, memoria.pacotes,
        memoria.cartoes, memoria.locacoes, memoria.pagamentos, memoria.avarias,
        memoria.comprovantes, memoria.eventos_auditoria,
    )
    for c in colecoes:
        c.clear()
    memoria._contadores.clear()
    yield
    fabrica.definir_repositorios(None)
    for c in colecoes:
        c.clear()
    memoria._contadores.clear()


# --- Interfaces e implementação em memória --------------------------------
@pytest.mark.parametrize("interface, modulo, campo", PARES)
def test_interface_e_abstrata(interface, modulo, campo):
    with pytest.raises(TypeError):
        interface()


@pytest.mark.parametrize("interface, modulo, campo", PARES)
def test_implementacao_em_memoria_cumpre_a_interface(interface, modulo, campo):
    assert isinstance(modulo.padrao, interface)
    assert not inspect.isabstract(type(modulo.padrao))
    for metodo in ("salvar", "list_all"):
        assert callable(getattr(modulo.padrao, metodo))


@pytest.mark.parametrize("interface, modulo, campo", PARES)
def test_fachada_de_modulo_continua_existindo_e_tem_salvar(interface, modulo, campo):
    assert callable(modulo.salvar)
    assert callable(modulo.list_all)


def test_interface_documenta_que_mutacao_sem_salvar_nao_persiste():
    doc = repositorios.__doc__ + (repositorios.Repositorio.__doc__ or "")
    assert "salvar" in doc
    assert "não" in doc and "forma suportada" in doc


# --- Fábrica --------------------------------------------------------------
@pytest.mark.parametrize("interface, modulo, campo", PARES)
def test_fabrica_devolve_as_instancias_padrao_em_memoria(interface, modulo, campo):
    assert getattr(fabrica.repositorios(), campo) is modulo.padrao


def test_fabrica_permite_trocar_e_voltar_ao_padrao():
    outro = dataclasses.replace(
        fabrica.repositorios_em_memoria(),
        bicicleta=repository_bicicleta.RepositorioBicicletaMemoria(),
    )
    fabrica.definir_repositorios(outro)
    assert fabrica.repositorios() is outro
    fabrica.definir_repositorios(None)
    assert fabrica.repositorios().bicicleta is repository_bicicleta.padrao


# --- salvar() -------------------------------------------------------------
def test_salvar_objeto_novo_gera_id_e_guarda():
    pagamento = Pagamento(10.0, TipoPagamento.CARTAO_CREDITO)
    assert pagamento.id is None
    salvo = repository_pagamento.padrao.salvar(pagamento)
    assert salvo is pagamento and pagamento.id == 1
    assert repository_pagamento.get_by_id(1) is pagamento


def test_salvar_objeto_existente_atualiza_sem_duplicar():
    estacao = repository_estacao.create("Centro", "Rua A", 0, 0, 5)
    estacao.set_status(StatusEstacao.BLOQUEADA)
    repository_estacao.padrao.salvar(estacao)
    assert repository_estacao.list_all() == [estacao]
    assert repository_estacao.get_by_id(estacao.id).status == StatusEstacao.BLOQUEADA


def test_fachada_e_classe_veem_os_mesmos_dados():
    bicicleta = repository_bicicleta.create(None)
    assert repository_bicicleta.padrao.get_by_id(bicicleta.id) is bicicleta
    assert fabrica.repositorios().bicicleta.get_by_qr(bicicleta.qr_code) is bicicleta


def test_usuario_salvar_usa_o_email_como_chave():
    usuario = Usuario("Ana", EMAIL)
    repository_usuario.padrao.salvar(usuario)
    assert repository_usuario.get_by_email(EMAIL) is usuario
    assert repository_usuario.list_all() == [usuario]


def _cartao(token="tok_1", apelido="pessoal"):
    return Cartao(
        token=token, ultimos_digitos="1234", bandeira="VISA", nome_titular="Ana",
        validade="12/30", tipo="CARTAO_CREDITO", apelido=apelido,
    )


def test_cartao_salvar_atualiza_o_cartao_vinculado():
    repository_cartao.add_cartao(EMAIL, _cartao())
    repository_cartao.padrao.salvar(_cartao(apelido="trabalho"))
    assert [c.apelido for c in repository_cartao.list_cartoes(EMAIL)] == ["trabalho"]
    assert len(repository_cartao.list_all()) == 1


def test_cartao_salvar_sem_vinculo_e_erro():
    with pytest.raises(ValueError):
        repository_cartao.padrao.salvar(_cartao())


# --- Services chamam salvar() depois de alterar ---------------------------
class _Espiao:
    """Embrulha um repositório e anota cada salvar()."""

    def __init__(self, real):
        self.real, self.salvos = real, []

    def salvar(self, obj):
        self.salvos.append(obj)
        return self.real.salvar(obj)

    def __getattr__(self, nome):
        return getattr(self.real, nome)


def _espionar(*campos):
    base = fabrica.repositorios_em_memoria()
    espioes = {c: _Espiao(getattr(base, c)) for c in campos}
    fabrica.definir_repositorios(dataclasses.replace(base, **espioes))
    return espioes


def test_troca_de_status_da_bicicleta_chama_salvar():
    estacao = repository_estacao.create("Centro", "Rua A", 0, 0, 5)
    bicicleta = repository_bicicleta.create(estacao)
    espioes = _espionar("bicicleta")

    bicicleta_service.alterar_status_manual(
        bicicleta.id, StatusBicicleta.BLOQUEADA, "adm@x.com"
    )

    assert espioes["bicicleta"].salvos == [bicicleta]


def test_troca_de_status_da_estacao_chama_salvar():
    estacao = repository_estacao.create("Centro", "Rua A", 0, 0, 5)
    espioes = _espionar("estacao")

    estacao_service.alterar_status_manual(estacao.id, StatusEstacao.BLOQUEADA, "adm@x.com")

    assert espioes["estacao"].salvos == [estacao]


def test_remover_bicicleta_da_estacao_salva_as_duas():
    estacao = repository_estacao.create("Centro", "Rua A", 0, 0, 5)
    bicicleta = repository_bicicleta.create(estacao)
    espioes = _espionar("estacao", "bicicleta")

    estacao_service.remover_bicicleta(bicicleta.id)

    assert espioes["estacao"].salvos == [estacao]
    assert espioes["bicicleta"].salvos == [bicicleta]


class _GatewayAprova:
    def cobrar(self, token, valor):
        return StatusPagamento.APROVADO


def test_status_do_pagamento_e_salvo_depois_da_transicao():
    repository_usuario.create(Usuario("Ana", EMAIL))
    repository_cartao.add_cartao(EMAIL, _cartao())
    estacao = repository_estacao.create("Centro", "Rua A", 0, 0, 5)
    locacao = repository_locacao.create(
        repository_usuario.get_by_email(EMAIL), repository_bicicleta.create(estacao), estacao
    )
    espioes = _espionar("pagamento")

    pagamento = PagamentoService(gateway=_GatewayAprova()).cobrar_corrida(EMAIL, 12.0, locacao.id)

    assert pagamento.status == StatusPagamento.APROVADO
    assert espioes["pagamento"].salvos == [pagamento]


class _PagamentosAprovados:
    def exigir_cartao_credito(self, email):
        return None

    def cobrar_pacote(self, email, valor, pacote_id):
        pagamento = Pagamento(valor, TipoPagamento.CARTAO_CREDITO)
        pagamento.aprovar()
        return pagamento


def test_pacote_ativado_e_consumido_e_salvo():
    repository_usuario.create(Usuario("Ana", EMAIL))
    agora = datetime(2026, 11, 27, 12, 0)
    espiao = _Espiao(repository_pacote.padrao)
    service = PacoteService(_PagamentosAprovados(), pacote_repo=espiao, relogio=lambda: agora)

    pacote, _ = service.comprar_pacote(EMAIL, 1)
    assert pacote.ativo and espiao.salvos == [pacote]  # ativação

    service.abater_minutos(EMAIL, 10)
    assert espiao.salvos == [pacote, pacote]  # saldo
    assert repository_pacote.get_by_id(pacote.id).minutos_restantes == pacote.minutos_totais - 10


# --- Regras de dependência ------------------------------------------------
def _importados(arquivo: Path) -> set[str]:
    nomes = set()
    for no in ast.walk(ast.parse(arquivo.read_text(encoding="utf-8"))):
        if isinstance(no, ast.Import):
            nomes |= {a.name for a in no.names}
        elif isinstance(no, ast.ImportFrom) and no.module:
            nomes.add(no.module)
            nomes |= {f"{no.module}.{a.name}" for a in no.names}
    return nomes


def _services():
    arquivos = sorted((RAIZ / "dominio").glob("*/service.py"))
    arquivos.append(RAIZ / "dominio" / "estacao" / "disponibilidade.py")
    return arquivos


def test_nenhum_service_importa_memoria_nem_os_modulos_repository():
    proibidos = []
    for arquivo in _services():
        for nome in _importados(arquivo):
            if nome.endswith(".memoria") or ".repository_" in nome:
                proibidos.append((arquivo.relative_to(RAIZ).as_posix(), nome))
    assert proibidos == []


def test_classes_de_dominio_nao_importam_repositorios():
    nao_sao_classes = {"service.py", "schemas.py", "schemas_disponibilidade.py",
                       "disponibilidade.py", "__init__.py"}
    proibidos = []
    for arquivo in (RAIZ / "dominio").rglob("*.py"):
        if arquivo.name in nao_sao_classes:
            continue
        for nome in _importados(arquivo):
            if ".repository_" in nome or nome.endswith((".repositorios", ".fabrica")):
                proibidos.append((arquivo.relative_to(RAIZ).as_posix(), nome))
    assert proibidos == []
