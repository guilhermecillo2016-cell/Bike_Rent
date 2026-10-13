"""
tests/test_contrato_front.py
------------------------------
Contrato entre o front (apresentacao/frontend/js) e a API: percorre as
jornadas das telas pelas rotas reais, mandando os mesmos corpos que o
JavaScript manda, e confere os campos que o JavaScript lê de cada
resposta. Se alguém renomear um campo da API, o teste acusa antes da tela
quebrar.

Rodar da raiz:  python -m pytest tests/test_contrato_front.py -q
"""

import pytest
from fastapi.testclient import TestClient

from apresentacao import adminweb
from main import app
from servicos_tecnicos.banco_de_dados import memoria
from servicos_tecnicos.iot import definir_trava
from servicos_tecnicos.iot.mock import ModoTrava, TravaInteligenteMock

COLECOES = (
    "usuarios", "estacoes", "bicicletas", "locacoes", "cartoes",
    "pacotes", "avarias", "eventos_auditoria", "pagamentos", "comprovantes",
)


@pytest.fixture(autouse=True)
def _limpa():
    for nome in COLECOES:
        getattr(memoria, nome).clear()
    memoria._contadores.clear()
    definir_trava(TravaInteligenteMock(ModoTrava.SUCESSO))
    yield
    definir_trava(None)


@pytest.fixture
def api():
    return TestClient(app)


def tem(corpo, *campos):
    faltando = [c for c in campos if c not in corpo]
    assert not faltando, f"faltam {faltando} em {sorted(corpo)}"


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def entrar(api, caminho, email, senha="123456"):
    """Login como o front faz: formulário com username/password."""
    r = api.post(caminho, data={"username": email, "password": senha})
    assert r.status_code == 200, r.text
    return auth(r.json()["access_token"])


CARTAO = {
    "tipo": "credito",
    "numero_cartao": "4111111111111111",
    "nome_titular": "CID CICLISTA",
    "validade": "12/30",
    "cvv": "123",
    "apelido": None,
}


@pytest.fixture
def equipe(api):
    """Administrador e operador logados, duas estações e três bicicletas."""
    r = api.post(
        "/adminweb/register",
        json={"nome": "Ana Admin", "email": "ana@x.com", "senha": "123456"},
        headers={"X-Admin-Secret": adminweb.ADMIN_SECRET},
    )
    assert r.status_code == 201, r.text
    admin = entrar(api, "/adminweb/login", "ana@x.com")

    estacoes = []
    for nome, lat, lng, cap in (("Centro", -27.60, -48.50, 3), ("Praia", -27.58, -48.52, 2)):
        r = api.post(
            "/adminweb/estacoes",
            json={"nome": nome, "endereco": f"Rua {nome}", "latitude": lat, "longitude": lng, "capacidade_total": cap},
            headers=admin,
        )
        assert r.status_code == 201, r.text
        estacoes.append(r.json())

    bicicletas = []
    for _ in range(2):
        r = api.post("/adminweb/bicicletas", json={"estacao_id": estacoes[0]["id"]}, headers=admin)
        assert r.status_code == 201, r.text
        bicicletas.append(r.json())

    r = api.post("/adminweb/operadores", json={"nome": "Olga Operadora", "email": "olga@x.com", "senha": "123456"}, headers=admin)
    assert r.status_code == 201, r.text
    operador = entrar(api, "/adminweb/login", "olga@x.com")
    return {"admin": admin, "operador": operador, "estacoes": estacoes, "bicicletas": bicicletas}


@pytest.fixture
def ciclista(api):
    """Ciclista cadastrado e logado, com o corpo de cadastro que o formulário envia."""
    r = api.post(
        "/webclient/register",
        json={
            "nome": "Cid Ciclista", "email": "cid@x.com", "senha": "123456",
            "cpf": "529.982.247-25", "telefone": "(48) 99999-8888", "endereco": None,
        },
    )
    assert r.status_code == 201, r.text
    return entrar(api, "/webclient/login", "cid@x.com")


# ----------------------------------------------------------------------
# Jornada do ciclista (index.html)
# ----------------------------------------------------------------------
def test_perfil_cartoes_e_estacoes(api, equipe, ciclista):
    eu = api.get("/webclient/me", headers=ciclista).json()
    tem(eu, "nome", "email", "cpf", "telefone", "endereco", "papel")
    assert eu["papel"] == "CICLISTA" and eu["cpf"].endswith("-25")

    r = api.post("/webclient/pagamentos", json=CARTAO, headers=ciclista)
    assert r.status_code == 201, r.text
    cartoes = api.get("/webclient/pagamentos", headers=ciclista).json()
    tem(cartoes[0], "token", "bandeira", "tipo", "apelido", "ultimos_digitos", "nome_titular", "validade")
    assert cartoes[0]["ultimos_digitos"] == "1111" and "cred" in cartoes[0]["tipo"].lower()

    # com lat/lng a lista vem ordenada pela distância (aba Estações, "Perto de mim")
    estacoes = api.get("/webclient/estacoes", params={"lat": -27.58, "lng": -48.52}).json()
    tem(estacoes[0], "id", "nome", "endereco", "status", "bicicletas_disponiveis", "vagas_livres", "distancia_metros")
    assert [e["nome"] for e in estacoes] == ["Praia", "Centro"]
    centro = next(e for e in estacoes if e["nome"] == "Centro")
    assert (centro["bicicletas_disponiveis"], centro["vagas_livres"]) == (2, 1)


def test_remover_cartao(api, ciclista):
    api.post("/webclient/pagamentos", json=CARTAO, headers=ciclista)
    token = api.get("/webclient/pagamentos", headers=ciclista).json()[0]["token"]
    assert api.delete(f"/webclient/pagamentos/{token}", headers=ciclista).status_code == 204
    assert api.get("/webclient/pagamentos", headers=ciclista).json() == []


def test_catalogo_e_compra_de_pacote(api, ciclista):
    catalogo = api.get("/webclient/pacotes/catalogo", headers=ciclista).json()
    tem(catalogo[0], "id", "minutos", "preco", "validade_dias")

    sem_cartao = api.post("/webclient/pacotes", json={"item_id": catalogo[0]["id"]}, headers=ciclista)
    assert sem_cartao.status_code == 400 and sem_cartao.json()["detail"]

    api.post("/webclient/pagamentos", json=CARTAO, headers=ciclista)
    r = api.post("/webclient/pacotes", json={"item_id": catalogo[0]["id"]}, headers=ciclista)
    assert r.status_code == 201, r.text
    tem(r.json(), "pacote", "pagamento_status")
    assert r.json()["pagamento_status"] == "APROVADO"

    meus = api.get("/webclient/pacotes", headers=ciclista).json()
    tem(meus[0], "id", "minutos_totais", "minutos_restantes", "data_validade", "ativo")
    assert meus[0]["ativo"] and meus[0]["minutos_restantes"] == catalogo[0]["minutos"]


def test_corrida_completa_do_qr_ao_comprovante(api, equipe, ciclista):
    api.post("/webclient/pagamentos", json=CARTAO, headers=ciclista)
    bike = equipe["bicicletas"][0]
    destino = equipe["estacoes"][1]

    v = api.post("/webclient/qr/validar", json={"qr_code": bike["qr_code"]}, headers=ciclista)
    assert v.status_code == 200, v.text
    tem(v.json(), "id", "qr_code", "estacao_id", "status", "bloqueio_pendente")

    r = api.post("/webclient/locacoes", json={"qr_code": bike["qr_code"]}, headers=ciclista)
    assert r.status_code == 201, r.text

    ativa = api.get("/webclient/locacoes/ativa", headers=ciclista).json()
    tem(ativa, "locacao_id", "bicicleta_id", "estacao_origem_nome", "duracao_segundos",
        "duracao_minutos", "minutos_pacote", "custo_estimado")
    assert ativa["estacao_origem_nome"] == "Centro" and ativa["bicicleta_id"] == bike["id"]

    # segunda corrida: o front lê a mensagem para decidir se vai à tela da corrida
    outra = api.post("/webclient/locacoes", json={"qr_code": equipe["bicicletas"][1]["qr_code"]}, headers=ciclista)
    assert outra.status_code == 409 and "corrida em andamento" in outra.json()["detail"]

    # o front SEMPRE manda descricao_avaria (texto ou null)
    enc = api.post("/webclient/locacoes/encerrar", json={"estacao_id": destino["id"], "descricao_avaria": None}, headers=ciclista)
    assert enc.status_code == 200, enc.text
    tem(enc.json(), "locacao_id", "data_hora_inicio", "data_hora_fim", "duracao_minutos", "minutos_pacote",
        "valor_total", "pagamento_status", "cobranca_pendente", "bicicleta_em_manutencao",
        "avaria_reportada", "comprovante_id")
    assert enc.json()["comprovante_id"] is not None and enc.json()["avaria_reportada"] is False

    comp = api.get(f"/webclient/locacoes/{enc.json()['locacao_id']}/comprovante", headers=ciclista)
    assert comp.status_code == 200, comp.text
    tem(comp.json(), "trajeto", "data_hora_inicio", "data_hora_fim", "duracao_minutos", "minutos_pacote",
        "metodo_pagamento", "pagamento_status", "tarifa_aplicada", "pago_com_pacote")
    assert comp.json()["trajeto"] == "Centro → Praia"

    # e a corrida acabou: o front volta para "Pronto para pedalar?"
    assert api.get("/webclient/locacoes/ativa", headers=ciclista).status_code == 404


def test_erros_que_a_tela_de_corrida_trata(api, equipe, ciclista):
    bike = equipe["bicicletas"][0]

    nao_existe = api.post("/webclient/qr/validar", json={"qr_code": "BIKE-NAOEXISTE"}, headers=ciclista)
    assert nao_existe.status_code == 404

    # sem cartão: validar passa, iniciar recusa com mensagem
    sem_cartao = api.post("/webclient/locacoes", json={"qr_code": bike["qr_code"]}, headers=ciclista)
    assert sem_cartao.status_code == 400 and sem_cartao.json()["detail"]

    # bicicleta em manutenção: 409 com sugestões (cada uma com qr_code e estacao_id)
    api.patch(f"/adminweb/bicicletas/{bike['id']}/status", json={"status": "EM_MANUTENCAO"}, headers=equipe["admin"])
    inapta = api.post("/webclient/qr/validar", json={"qr_code": bike["qr_code"]}, headers=ciclista)
    assert inapta.status_code == 409
    tem(inapta.json(), "detail", "sugestoes")
    tem(inapta.json()["sugestoes"][0], "id", "qr_code", "estacao_id")

    # trava que não abre: 503 e a bicicleta continua parada
    api.post("/webclient/pagamentos", json=CARTAO, headers=ciclista)
    definir_trava(TravaInteligenteMock(ModoTrava.TIMEOUT))
    livre = equipe["bicicletas"][1]
    trava = api.post("/webclient/locacoes", json={"qr_code": livre["qr_code"]}, headers=ciclista)
    assert trava.status_code == 503 and trava.json()["detail"]
    assert api.get("/webclient/locacoes/ativa", headers=ciclista).status_code == 404

    # encerrar sem corrida: a mensagem cita "corrida" (o front usa isso)
    sem_corrida = api.post("/webclient/locacoes/encerrar", json={"estacao_id": 1, "descricao_avaria": None}, headers=ciclista)
    assert sem_corrida.status_code == 404 and "corrida" in sem_corrida.json()["detail"]


def test_devolucao_em_estacao_lotada_traz_sugestoes(api, equipe, ciclista):
    api.post("/webclient/pagamentos", json=CARTAO, headers=ciclista)
    praia = equipe["estacoes"][1]
    for _ in range(praia["capacidade_total"]):  # enche a Praia
        assert api.post("/adminweb/bicicletas", json={"estacao_id": praia["id"]}, headers=equipe["admin"]).status_code == 201
    api.post("/webclient/locacoes", json={"qr_code": equipe["bicicletas"][0]["qr_code"]}, headers=ciclista)

    r = api.post("/webclient/locacoes/encerrar", json={"estacao_id": praia["id"], "descricao_avaria": None}, headers=ciclista)
    assert r.status_code == 409
    tem(r.json(), "detail", "sugestoes")
    tem(r.json()["sugestoes"][0], "id", "nome", "endereco", "vagas_disponiveis")
    assert any(s["nome"] == "Centro" for s in r.json()["sugestoes"])


def test_avaria_no_encerramento_e_resolucao_pelo_operador(api, equipe, ciclista):
    api.post("/webclient/pagamentos", json=CARTAO, headers=ciclista)
    bike = equipe["bicicletas"][0]
    api.post("/webclient/locacoes", json={"qr_code": bike["qr_code"]}, headers=ciclista)
    enc = api.post(
        "/webclient/locacoes/encerrar",
        json={"estacao_id": equipe["estacoes"][1]["id"], "descricao_avaria": "pneu furado"},
        headers=ciclista,
    ).json()
    assert enc["avaria_reportada"] is True and enc["bicicleta_em_manutencao"] is True

    avarias = api.get("/adminweb/avarias", headers=equipe["admin"]).json()
    tem(avarias[0], "id", "descricao", "data_hora", "usuario_email", "bicicleta_id", "status")
    assert avarias[0]["status"] == "PENDENTE"

    # só o operador resolve (a tela esconde o botão para o administrador)
    assert api.patch(f"/adminweb/avarias/{avarias[0]['id']}/resolver", headers=equipe["admin"]).status_code == 403
    r = api.patch(f"/adminweb/avarias/{avarias[0]['id']}/resolver", headers=equipe["operador"])
    assert r.status_code == 200 and r.json()["status"] == "RESOLVIDO"

    frota = api.get("/adminweb/bicicletas", headers=equipe["operador"]).json()
    assert next(b for b in frota if b["id"] == bike["id"])["status"] == "DISPONIVEL"


# ----------------------------------------------------------------------
# Painel de gestão (gestao.html)
# ----------------------------------------------------------------------
def test_listas_e_alteracoes_de_status_da_gestao(api, equipe):
    estacoes = api.get("/adminweb/estacoes", headers=equipe["operador"]).json()
    tem(estacoes[0], "id", "nome", "endereco", "latitude", "longitude", "capacidade_total",
        "vagas_disponiveis", "bicicletas_disponiveis", "status")

    r = api.patch(f"/adminweb/estacoes/{estacoes[0]['id']}/status", json={"status": "BLOQUEADA"}, headers=equipe["operador"])
    assert r.status_code == 200 and r.json()["status"] == "BLOQUEADA"

    frota = api.get("/adminweb/bicicletas", params={"status": "DISPONIVEL"}, headers=equipe["operador"]).json()
    tem(frota[0], "id", "qr_code", "status", "estacao_id", "bloqueio_pendente")
    r = api.patch(f"/adminweb/bicicletas/{frota[0]['id']}/status", json={"status": "BLOQUEADA"}, headers=equipe["operador"])
    assert r.status_code == 200 and r.json()["status"] == "BLOQUEADA"

    auditoria = api.get("/adminweb/auditoria", headers=equipe["admin"]).json()
    tem(auditoria[0], "id", "data_hora", "usuario_email", "tipo_entidade", "entidade_id", "status_anterior", "status_novo")
    assert len(auditoria) == 2


def test_relatorio_tem_todos_os_campos_que_a_tela_mostra(api, equipe, ciclista):
    api.post("/webclient/pagamentos", json=CARTAO, headers=ciclista)
    api.post("/webclient/locacoes", json={"qr_code": equipe["bicicletas"][0]["qr_code"]}, headers=ciclista)
    api.post("/webclient/locacoes/encerrar", json={"estacao_id": equipe["estacoes"][1]["id"], "descricao_avaria": None}, headers=ciclista)

    r = api.get("/adminweb/relatorios", headers=equipe["admin"])
    assert r.status_code == 200, r.text
    tem(r.json(), "data_geracao", "inicio", "fim", "estacao_id", "receita_total", "receita_corridas",
        "receita_pacotes", "total_locacoes", "bicicletas_total", "bicicletas_ociosas", "taxa_ociosidade",
        "total_avarias", "indice_quebras", "horarios_pico")
    tem(r.json()["horarios_pico"][0], "estacao_id", "estacao_nome", "total_locacoes", "hora_pico", "locacoes_na_hora_pico")

    filtrado = api.get(
        "/adminweb/relatorios",
        params={"inicio": "2020-01-01", "fim": "2020-01-31", "estacao_id": equipe["estacoes"][0]["id"]},
        headers=equipe["admin"],
    )
    assert filtrado.status_code == 200 and filtrado.json()["total_locacoes"] == 0


def test_o_que_cada_papel_nao_pode_fazer_na_gestao(api, equipe, ciclista):
    op, adm = equipe["operador"], equipe["admin"]
    assert api.get("/adminweb/relatorios", headers=op).status_code == 403
    assert api.get("/adminweb/auditoria", headers=op).status_code == 403
    assert api.post("/adminweb/operadores", json={"nome": "X", "email": "x@x.com", "senha": "123456"}, headers=op).status_code == 403
    assert api.post("/adminweb/bicicletas", json={"estacao_id": 1}, headers=op).status_code == 403
    assert api.get("/adminweb/estacoes", headers=ciclista).status_code == 403
    # a tela de entrada de cada lado recusa o papel errado e mostra o motivo
    assert api.post("/webclient/login", data={"username": "ana@x.com", "password": "123456"}).status_code == 403
    assert api.post("/adminweb/login", data={"username": "cid@x.com", "password": "123456"}).status_code == 403
    assert api.get("/adminweb/avarias", headers=adm).status_code == 200


# ----------------------------------------------------------------------
# Regressões de back-end encontradas ao montar o front
# ----------------------------------------------------------------------
def test_estacoes_publicas_trazem_coordenadas_para_o_mapa(api, equipe):
    estacoes = api.get("/webclient/estacoes").json()
    tem(estacoes[0], "latitude", "longitude")
    centro = next(e for e in estacoes if e["nome"] == "Centro")
    assert (centro["latitude"], centro["longitude"]) == (-27.60, -48.50)


def test_lista_publica_de_estacoes_nao_quebra_com_estacao_real(api, equipe):
    r = api.get("/webclient/estacoes")
    assert r.status_code == 200 and len(r.json()) == 2


def test_encerrar_sem_o_campo_descricao_avaria_funciona(api, equipe, ciclista):
    api.post("/webclient/pagamentos", json=CARTAO, headers=ciclista)
    api.post("/webclient/locacoes", json={"qr_code": equipe["bicicletas"][0]["qr_code"]}, headers=ciclista)
    r = api.post("/webclient/locacoes/encerrar", json={"estacao_id": equipe["estacoes"][1]["id"]}, headers=ciclista)
    assert r.status_code == 200 and r.json()["avaria_reportada"] is False
