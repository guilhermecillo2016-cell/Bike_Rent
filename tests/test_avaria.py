from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from main import app
from dominio.avaria import service as avaria_service
from dominio.bicicleta import service as bicicleta_service
from dominio.bicicleta.schemas import BicicletaCreate
from dominio.estacao import service as estacao_service
from dominio.estacao.schemas import EstacaoCreate
from dominio.locacao import service as locacao_service
from dominio.pagamento import service as pagamento_service
from dominio.pagamento.schemas import CartaoCreate
from dominio.usuario import service as usuario_service
from servicos_tecnicos.banco_de_dados import memoria
from servicos_tecnicos.banco_de_dados.enums import (
    PapelUsuario, StatusAvaria, StatusBicicleta, StatusPagamento,
)
from servicos_tecnicos.banco_de_dados.models import UsuarioORM
from servicos_tecnicos.iot import definir_trava
from servicos_tecnicos.iot.mock import ModoTrava, TravaInteligenteMock

EMAIL = "c@x.com"
OP = "op@x.com"


@pytest.fixture(autouse=True)
def _limpa(monkeypatch):
    for d in (memoria.estacoes, memoria.bicicletas, memoria.locacoes, memoria.cartoes,
              memoria.pacotes, memoria.avarias, memoria.eventos_auditoria, memoria.usuarios):
        d.clear()
    memoria._contadores.clear()
    definir_trava(TravaInteligenteMock(ModoTrava.SUCESSO))
    monkeypatch.setattr(
        pagamento_service.PagamentoService, "cobrar_corrida",
        lambda self, email, valor, locacao_id: SimpleNamespace(status=StatusPagamento.APROVADO),
    )
    yield
    definir_trava(None)


def _estacao(nome="E", lat=0.0):
    return estacao_service.criar_estacao(
        EstacaoCreate(nome=nome, endereco="Rua", latitude=lat, longitude=0, capacidade_total=10)
    )


def _corrida():
    origem, destino = _estacao("Origem"), _estacao("Destino", lat=0.01)
    bike = bicicleta_service.cadastrar_bicicleta(BicicletaCreate(estacao_id=origem.id))
    pagamento_service.vincular_cartao(
        EMAIL,
        CartaoCreate(numero_cartao="4111111111111111", nome_titular="Fulano",
                     validade="12/99", cvv="123"),
    )
    locacao_service.iniciar_locacao(EMAIL, bike.qr_code)
    return destino, bike


def _bike_com_avaria():
    destino, bike = _corrida()
    locacao_service.encerrar_locacao(EMAIL, destino.id, descricao_avaria="Pneu furado")
    return destino, bike, list(memoria.avarias.values())[-1]


def _token(email, papel):
    memoria.usuarios[email] = UsuarioORM(nome="x", email=email, senha_hash="x", papel=papel)
    return {"Authorization": f"Bearer {usuario_service.create_access_token({'sub': email})}"}


def test_reporte_no_encerramento_bloqueia_a_bicicleta():
    destino, bike = _corrida()
    r = locacao_service.encerrar_locacao(EMAIL, destino.id, descricao_avaria="Freio solto")

    assert r.avaria_reportada is True and r.bicicleta_em_manutencao is True
    assert bike.status == StatusBicicleta.EM_MANUTENCAO
    assert estacao_service.bicicletas_disponiveis(destino) == 0  # não aparece como disponível
    avaria = list(memoria.avarias.values())[-1]
    assert avaria.status == StatusAvaria.PENDENTE
    assert (avaria.bicicleta_id, avaria.usuario_email) == (bike.id, EMAIL)
    with pytest.raises(bicicleta_service.BicicletaIndisponivel):
        bicicleta_service.validar_qr(bike.qr_code)


def test_encerrar_sem_descricao_nao_cria_avaria():
    destino, bike = _corrida()
    r = locacao_service.encerrar_locacao(EMAIL, destino.id, descricao_avaria="   ")
    assert r.avaria_reportada is False
    assert memoria.avarias == {} and bike.status == StatusBicicleta.DISPONIVEL


def test_travamento_falho_nao_registra_avaria():
    destino, bike = _corrida()
    definir_trava(TravaInteligenteMock(ModoTrava.TIMEOUT))
    with pytest.raises(HTTPException):
        locacao_service.encerrar_locacao(EMAIL, destino.id, descricao_avaria="Pneu furado")
    assert memoria.avarias == {} and bike.status == StatusBicicleta.EM_USO


def test_bike_com_avaria_nao_pode_ser_liberada_a_mao():
    _, bike, _ = _bike_com_avaria()
    with pytest.raises(HTTPException) as e:
        bicicleta_service.alterar_status_manual(bike.id, StatusBicicleta.DISPONIVEL, OP)
    assert e.value.status_code == 409


def test_resolver_unica_avaria_libera_e_audita():
    _, bike, avaria = _bike_com_avaria()
    avaria_service.resolver_avaria(avaria.id, OP)
    assert avaria.status == StatusAvaria.RESOLVIDO
    assert bike.status == StatusBicicleta.DISPONIVEL
    ultimo = list(memoria.eventos_auditoria.values())[-1]
    assert (ultimo.usuario_email, ultimo.status_novo) == (OP, str(StatusBicicleta.DISPONIVEL))


def test_resolver_com_outra_avaria_pendente_nao_libera():
    _, bike, primeira = _bike_com_avaria()
    avaria_service.reportar_avaria(EMAIL, bike.id, "Corrente solta")
    avaria_service.resolver_avaria(primeira.id, OP)
    assert bike.status == StatusBicicleta.EM_MANUTENCAO


def test_resolver_com_bicicleta_bloqueada_continua_bloqueada():
    _, bike, avaria = _bike_com_avaria()
    bicicleta_service.alterar_status_manual(bike.id, StatusBicicleta.BLOQUEADA, "adm@x.com")
    avaria_service.resolver_avaria(avaria.id, OP)
    assert avaria.status == StatusAvaria.RESOLVIDO
    assert bike.status == StatusBicicleta.BLOQUEADA


def test_resolver_inexistente_404_e_duas_vezes_409():
    with pytest.raises(HTTPException) as e:
        avaria_service.resolver_avaria(999, OP)
    assert e.value.status_code == 404
    _, _, avaria = _bike_com_avaria()
    avaria_service.resolver_avaria(avaria.id, OP)
    with pytest.raises(HTTPException) as e:
        avaria_service.resolver_avaria(avaria.id, OP)
    assert e.value.status_code == 409


def test_somente_operador_resolve():
    _, _, avaria = _bike_com_avaria()
    client = TestClient(app)
    url = f"/adminweb/avarias/{avaria.id}/resolver"

    assert client.patch(url, headers=_token("adm@x.com", PapelUsuario.ADMINISTRADOR)).status_code == 403
    assert client.patch(url, headers=_token(EMAIL, PapelUsuario.CICLISTA)).status_code == 403
    r = client.patch(url, headers=_token(OP, PapelUsuario.OPERADOR_CAMPO))
    assert r.status_code == 200 and r.json()["status"] == "RESOLVIDO"


def test_listar_com_filtro_de_status():
    _, bike, primeira = _bike_com_avaria()
    avaria_service.reportar_avaria(EMAIL, bike.id, "Corrente solta")
    avaria_service.resolver_avaria(primeira.id, OP)
    client = TestClient(app)
    headers = _token("adm@x.com", PapelUsuario.ADMINISTRADOR)

    assert len(client.get("/adminweb/avarias", headers=headers).json()) == 2
    pendentes = client.get("/adminweb/avarias?status=PENDENTE", headers=headers).json()
    assert [a["descricao"] for a in pendentes] == ["Corrente solta"]