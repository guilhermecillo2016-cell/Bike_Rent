/*
 * js/gestao.js
 * ----------------------------------------------------------------
 * Painel da equipe (gestao.html) — A7. Administrador vê tudo; operador
 * de campo vê estações, bicicletas e avarias (e resolve avarias).
 * Depende de js/util.js e js/app.js.
 */
(function () {
  "use strict";

  const { $, el, limpar, selo, mostrarMsg, limparMsg, toast, carregando } = App;
  const api = App.criarCliente("rota_admin_token");

  const estado = { usuario: null, estacoes: [] };
  const ehAdmin = () => !!estado.usuario && estado.usuario.papel === "ADMINISTRADOR";
  const PAPEIS_EQUIPE = ["ADMINISTRADOR", "OPERADOR_CAMPO"];
  const ROTULO_PAPEL = { ADMINISTRADOR: "Administrador", OPERADOR_CAMPO: "Operador de campo" };

  // Status que a equipe pode escolher (EM_USO só a locação coloca)
  const OPCOES_BICICLETA = {
    DISPONIVEL: Util.STATUS_BICICLETA.DISPONIVEL,
    EM_MANUTENCAO: Util.STATUS_BICICLETA.EM_MANUTENCAO,
    BLOQUEADA: Util.STATUS_BICICLETA.BLOQUEADA,
  };
  const OPCOES_ESTACAO = Util.STATUS_ESTACAO;

  // ==================================================================
  // Entrada
  // ==================================================================
  function mostrarEntrada(qual) {
    const login = qual === "login";
    $("tab-login").setAttribute("aria-selected", String(login));
    $("tab-register").setAttribute("aria-selected", String(!login));
    $("form-login").classList.toggle("active", login);
    $("form-register").classList.toggle("active", !login);
  }
  $("tab-login").addEventListener("click", () => mostrarEntrada("login"));
  $("tab-register").addEventListener("click", () => mostrarEntrada("register"));

  $("form-register").addEventListener("submit", async (e) => {
    e.preventDefault();
    const msg = $("register-msg");
    limparMsg(msg);
    const botao = e.target.querySelector(".btn");
    const corpo = {
      nome: $("reg-nome").value.trim(),
      email: $("reg-email").value.trim(),
      senha: $("reg-password").value,
    };
    carregando(botao, true, "Cadastrar administrador");
    const r = await api.cadastrar("/adminweb/register", corpo, { "X-Admin-Secret": $("reg-secret").value });
    carregando(botao, false, "Cadastrar administrador");
    if (!r.ok) return mostrarMsg(msg, Util.erroTexto(r.data, "Não foi possível cadastrar o administrador."), "error");
    mostrarMsg(msg, "Administrador criado. Agora entre com esses dados.", "success");
    $("login-email").value = corpo.email;
    e.target.reset();
    setTimeout(() => mostrarEntrada("login"), 900);
  });

  $("form-login").addEventListener("submit", async (e) => {
    e.preventDefault();
    const msg = $("login-msg");
    limparMsg(msg);
    const botao = e.target.querySelector(".btn");
    carregando(botao, true, "Entrar", "Entrando...");
    const r = await api.entrar("/adminweb/login", $("login-email").value.trim(), $("login-password").value);
    carregando(botao, false, "Entrar");
    if (!r.ok) return mostrarMsg(msg, Util.erroTexto(r.data, "E-mail ou senha incorretos."), "error");
    api.guardarToken(r.data.access_token);
    e.target.reset();
    await carregarSessao();
  });

  function mostrarTelaEntrada() {
    $("tela-app").hidden = true;
    $("tela-auth").hidden = false;
  }

  let expirando = false;
  function sair(expirou) {
    api.sair();
    estado.usuario = null;
    estado.estacoes = [];
    if (expirou) toast("Sua sessão expirou. Entre novamente.", "error");
    mostrarTelaEntrada();
    mostrarEntrada("login");
  }
  api.aoExpirar(() => {
    if (expirando) return;
    expirando = true;
    sair(true);
    setTimeout(() => (expirando = false), 500);
  });
  $("btn-sair").addEventListener("click", () => sair(false));

  async function carregarSessao() {
    if (!api.token()) return mostrarTelaEntrada();
    const r = await api.get("/webclient/me");
    if (!r.ok) {
      if (r.status !== 0) api.sair();
      return mostrarTelaEntrada();
    }
    if (!PAPEIS_EQUIPE.includes(r.data.papel)) {
      api.sair();
      mostrarTelaEntrada();
      return mostrarMsg($("login-msg"), "Essa conta não tem acesso ao painel de gestão.", "error");
    }
    estado.usuario = r.data;
    entrarNoPainel();
  }

  function entrarNoPainel() {
    $("tela-auth").hidden = true;
    $("tela-app").hidden = false;
    $("topo-nome").textContent = estado.usuario.nome || estado.usuario.email;
    const papel = $("topo-papel");
    papel.textContent = ROTULO_PAPEL[estado.usuario.papel];
    papel.className = `selo ${ehAdmin() ? "ok" : "info"}`;
    for (const n of document.querySelectorAll("[data-so-admin]")) n.hidden = !ehAdmin();
    $("avarias-ajuda").textContent = ehAdmin()
      ? "Reportadas pelos ciclistas ao devolver a bicicleta. Quem marca como resolvida é o operador de campo."
      : "Reportadas pelos ciclistas ao devolver a bicicleta. Depois do reparo, marque como resolvida.";
    abas.selecionar("estacoes");
  }

  // ==================================================================
  // Abas
  // ==================================================================
  const abas = App.criarAbas(Array.from(document.querySelectorAll(".tabbar button")), {
    async aoMudar(nome) {
      if (!estado.usuario) return;
      if (nome === "estacoes") await carregarEstacoes();
      if (nome === "bicicletas") {
        await carregarEstacoes();
        await carregarBicicletas();
      }
      if (nome === "avarias") await carregarAvarias();
      if (nome === "relatorios") await carregarEstacoes();
      if (nome === "auditoria") await carregarAuditoria();
      window.scrollTo({ top: 0 });
    },
  });

  // ==================================================================
  // Peças reutilizadas
  // ==================================================================
  function celulaTexto(texto) {
    return el("td", { text: texto });
  }

  /** Célula com seletor de status + botão Aplicar. */
  function celulaAcao(opcoes, atual, aplicar) {
    const seletor = el(
      "select",
      { "aria-label": "Novo status" },
      Object.entries(opcoes).map(([valor, rotulo]) => el("option", { value: valor, text: rotulo })),
    );
    seletor.value = atual in opcoes ? atual : Object.keys(opcoes)[0];
    const botao = el("button", { class: "btn secondary pequeno", type: "button", text: "Aplicar" });
    botao.addEventListener("click", () => aplicar(seletor.value, botao));
    return el("td", {}, el("div", { class: "acao" }, seletor, botao));
  }

  function preencherSeletor(seletor, pares, rotuloTodos) {
    const atual = seletor.value;
    limpar(seletor);
    if (rotuloTodos) seletor.append(el("option", { value: "", text: rotuloTodos }));
    for (const [valor, rotulo] of pares) seletor.append(el("option", { value: String(valor), text: rotulo }));
    if (Array.from(seletor.options).some((o) => o.value === atual)) seletor.value = atual;
  }

  function nomeDaEstacao(id) {
    const e = estado.estacoes.find((x) => x.id === id);
    return e ? e.nome : `Estação ${id}`;
  }

  function alternarTabela(tabelaId, vazioId, temLinhas) {
    $(tabelaId).hidden = !temLinhas;
    $(vazioId).hidden = temLinhas;
  }

  async function enviarStatus(url, status, msgId, botao) {
    const msg = $(msgId);
    limparMsg(msg);
    botao.disabled = true;
    const r = await api.patch(url, { status });
    botao.disabled = false;
    if (!r.ok) {
      mostrarMsg(msg, Util.erroTexto(r.data, "Não foi possível alterar o status."), "error");
      return null;
    }
    return r.data;
  }

  // ==================================================================
  // ESTAÇÕES
  // ==================================================================
  async function carregarEstacoes() {
    const r = await api.get("/adminweb/estacoes");
    if (!r.ok) return;
    estado.estacoes = r.data;
    renderEstacoes();
    atualizarSeletoresDeEstacao();
  }

  function renderEstacoes() {
    const corpo = limpar($("estacoes-corpo"));
    alternarTabela("estacoes-tabela", "estacoes-vazio", estado.estacoes.length > 0);
    for (const e of estado.estacoes) {
      corpo.append(
        el(
          "tr",
          {},
          celulaTexto(e.nome),
          celulaTexto(e.endereco),
          celulaTexto(`${e.latitude.toFixed(4)}, ${e.longitude.toFixed(4)}`),
          celulaTexto(String(e.bicicletas_disponiveis)),
          celulaTexto(`${e.vagas_disponiveis}/${e.capacidade_total}`),
          el("td", {}, selo(e.status)),
          celulaAcao(OPCOES_ESTACAO, e.status, (status, botao) => alterarStatusEstacao(e.id, status, botao)),
        ),
      );
    }
  }

  function atualizarSeletoresDeEstacao() {
    const pares = estado.estacoes.map((e) => [e.id, `${e.nome} (${Util.plural(e.vagas_disponiveis, "vaga livre", "vagas livres")})`]);
    preencherSeletor($("bike-estacao"), pares.length ? pares : [], null);
    if (!pares.length) $("bike-estacao").append(el("option", { value: "", text: "Cadastre uma estação primeiro", disabled: true, selected: true }));
    preencherSeletor($("filtro-bike-estacao"), estado.estacoes.map((e) => [e.id, e.nome]), "Todas as estações");
    preencherSeletor($("rel-estacao"), estado.estacoes.map((e) => [e.id, e.nome]), "Todas as estações");
  }

  async function alterarStatusEstacao(id, status, botao) {
    const dados = await enviarStatus(`/adminweb/estacoes/${id}/status`, status, "acao-estacao-msg", botao);
    if (!dados) return;
    mostrarMsg($("acao-estacao-msg"), "Status da estação atualizado.", "success");
    await carregarEstacoes();
  }

  $("form-estacao").addEventListener("submit", async (e) => {
    e.preventDefault();
    const msg = $("estacao-msg");
    limparMsg(msg);
    const botao = e.target.querySelector('button[type="submit"]');
    const numero = (id) => parseFloat($(id).value.replace(",", "."));
    const corpo = {
      nome: $("est-nome").value.trim(),
      endereco: $("est-endereco").value.trim(),
      latitude: numero("est-lat"),
      longitude: numero("est-lng"),
      capacidade_total: parseInt($("est-capacidade").value, 10),
    };
    if (Number.isNaN(corpo.latitude) || Number.isNaN(corpo.longitude) || Number.isNaN(corpo.capacidade_total)) {
      return mostrarMsg(msg, "Preencha latitude, longitude e capacidade com números.", "error");
    }
    carregando(botao, true, "Criar estação");
    const r = await api.post("/adminweb/estacoes", corpo);
    carregando(botao, false, "Criar estação");
    if (!r.ok) return mostrarMsg(msg, Util.erroTexto(r.data, "Não foi possível criar a estação."), "error");
    mostrarMsg(msg, "Estação criada com sucesso.", "success");
    e.target.reset();
    await carregarEstacoes();
  });

  $("btn-usar-localizacao").addEventListener("click", async () => {
    const botao = $("btn-usar-localizacao");
    botao.disabled = true;
    try {
      const pos = await App.localizar();
      $("est-lat").value = pos.lat.toFixed(6);
      $("est-lng").value = pos.lng.toFixed(6);
      toast("Coordenadas preenchidas com a sua localização.", "success");
    } catch (erro) {
      toast(erro.message, "error");
    } finally {
      botao.disabled = false;
    }
  });
  $("btn-atualizar-estacoes").addEventListener("click", carregarEstacoes);

  // ==================================================================
  // BICICLETAS
  // ==================================================================
  async function carregarBicicletas() {
    const filtros = new URLSearchParams();
    if ($("filtro-bike-status").value) filtros.set("status", $("filtro-bike-status").value);
    if ($("filtro-bike-estacao").value) filtros.set("estacao_id", $("filtro-bike-estacao").value);
    const consulta = filtros.toString() ? `?${filtros}` : "";
    const r = await api.get(`/adminweb/bicicletas${consulta}`);
    if (!r.ok) return;
    renderBicicletas(r.data);
  }

  function renderBicicletas(bicicletas) {
    const corpo = limpar($("bicicletas-corpo"));
    alternarTabela("bicicletas-tabela", "bicicletas-vazio", bicicletas.length > 0);
    for (const b of bicicletas) {
      const status = el("td", {}, selo(b.status));
      if (b.bloqueio_pendente) status.append(el("div", { class: "opcional", style: "font-size:0.78rem; margin-top:4px", text: "bloqueio agendado para o fim da corrida" }));
      corpo.append(
        el(
          "tr",
          {},
          celulaTexto(`#${b.id}`),
          el(
            "td",
            {},
            el("span", { class: "mono", text: b.qr_code }),
            " ",
            el("button", { class: "btn-link", type: "button", text: "Ver QR", onclick: () => abrirQr(b) }),
          ),
          status,
          celulaTexto(b.estacao_id == null ? "Em corrida" : nomeDaEstacao(b.estacao_id)),
          celulaAcao(OPCOES_BICICLETA, b.status, (novo, botao) => alterarStatusBicicleta(b.id, novo, botao)),
        ),
      );
    }
  }

  async function alterarStatusBicicleta(id, status, botao) {
    const dados = await enviarStatus(`/adminweb/bicicletas/${id}/status`, status, "acao-bicicleta-msg", botao);
    if (!dados) return;
    const agendado = dados.status === "EM_USO" && dados.bloqueio_pendente;
    mostrarMsg(
      $("acao-bicicleta-msg"),
      agendado
        ? "A bicicleta está em corrida. Ela será colocada em manutenção quando a corrida terminar."
        : "Status da bicicleta atualizado.",
      "success",
    );
    await carregarEstacoes();
    await carregarBicicletas();
  }

  $("form-bicicleta").addEventListener("submit", async (e) => {
    e.preventDefault();
    const msg = $("bicicleta-msg");
    limparMsg(msg);
    const botao = e.target.querySelector('button[type="submit"]');
    const estacaoId = parseInt($("bike-estacao").value, 10);
    if (!estacaoId) return mostrarMsg(msg, "Cadastre uma estação primeiro.", "error");
    carregando(botao, true, "Cadastrar bicicleta");
    const r = await api.post("/adminweb/bicicletas", { estacao_id: estacaoId });
    carregando(botao, false, "Cadastrar bicicleta");
    if (!r.ok) return mostrarMsg(msg, Util.erroTexto(r.data, "Não foi possível cadastrar a bicicleta."), "error");
    mostrarMsg(msg, `Bicicleta #${r.data.id} cadastrada. Código: ${r.data.qr_code} (use “Ver QR” na tabela para imprimir).`, "success");
    await carregarEstacoes();
    await carregarBicicletas();
  });

  $("filtro-bike-status").addEventListener("change", carregarBicicletas);
  $("filtro-bike-estacao").addEventListener("change", carregarBicicletas);
  $("btn-atualizar-bicicletas").addEventListener("click", async () => {
    await carregarEstacoes();
    await carregarBicicletas();
  });

  // ---------- QR Code imprimível ----------
  async function abrirQr(b) {
    $("qr-titulo").textContent = `Bicicleta #${b.id}`;
    $("qr-texto").textContent = b.qr_code;
    const alvo = limpar($("qr-imagem"));
    alvo.append(el("div", { class: "girando" }));
    const caixa = $("modal-qr");
    if (typeof caixa.showModal === "function") caixa.showModal();
    else caixa.setAttribute("open", "");
    try {
      const qrcode = await App.bibliotecas.qrcode();
      const qr = qrcode(0, "M");
      qr.addData(b.qr_code);
      qr.make();
      alvo.innerHTML = qr.createSvgTag({ cellSize: 6, margin: 2, scalable: true });
    } catch (_) {
      limpar(alvo);
      alvo.append(el("p", { class: "sub", text: "Não foi possível gerar a imagem (sem internet?). Use o código abaixo." }));
    }
  }
  $("btn-fechar-qr").addEventListener("click", () => {
    const caixa = $("modal-qr");
    if (typeof caixa.close === "function") caixa.close();
    else caixa.removeAttribute("open");
  });
  $("btn-imprimir-qr").addEventListener("click", () => window.print());

  // ==================================================================
  // AVARIAS
  // ==================================================================
  async function carregarAvarias() {
    const filtro = $("filtro-avaria-status").value;
    const r = await api.get(`/adminweb/avarias${filtro ? `?status=${filtro}` : ""}`);
    if (!r.ok) return;
    renderAvarias(r.data);
  }

  function celulaResolver(a) {
    if (a.status === "RESOLVIDO") return el("td", { text: "—" });
    if (estado.usuario.papel !== "OPERADOR_CAMPO") {
      return el("td", {}, el("span", { class: "opcional", style: "font-size:0.8rem", text: "o operador resolve" }));
    }
    const botao = el("button", { class: "btn pequeno", type: "button", text: "Marcar como resolvida" });
    botao.addEventListener("click", () => resolverAvaria(a, botao));
    return el("td", {}, botao);
  }

  function renderAvarias(avarias) {
    const corpo = limpar($("avarias-corpo"));
    alternarTabela("avarias-tabela", "avarias-vazio", avarias.length > 0);
    for (const a of avarias) {
      corpo.append(
        el(
          "tr",
          {},
          celulaTexto(`#${a.id}`),
          celulaTexto(`#${a.bicicleta_id}`),
          celulaTexto(a.descricao),
          celulaTexto(a.usuario_email),
          celulaTexto(Util.dataHora(a.data_hora)),
          el("td", {}, selo(a.status)),
          celulaResolver(a),
        ),
      );
    }
  }

  async function resolverAvaria(a, botao) {
    const msg = $("acao-avaria-msg");
    limparMsg(msg);
    botao.disabled = true;
    const r = await api.patch(`/adminweb/avarias/${a.id}/resolver`);
    botao.disabled = false;
    if (!r.ok) return mostrarMsg(msg, Util.erroTexto(r.data, "Não foi possível resolver a avaria."), "error");
    mostrarMsg(msg, `Avaria #${a.id} resolvida. Se a bicicleta não tem outras pendências, ela volta a ficar disponível.`, "success");
    await carregarAvarias();
  }

  $("filtro-avaria-status").addEventListener("change", carregarAvarias);
  $("btn-atualizar-avarias").addEventListener("click", carregarAvarias);

  // ==================================================================
  // RELATÓRIOS (só administrador)
  // ==================================================================
  const dataBR = (iso) => iso.split("-").reverse().join("/");

  function renderRelatorio(r) {
    const periodo =
      r.inicio || r.fim
        ? `${r.inicio ? dataBR(r.inicio) : "o início"} até ${r.fim ? dataBR(r.fim) : "hoje"}`
        : "todo o período";
    const estacao = r.estacao_id == null ? "todas as estações" : nomeDaEstacao(r.estacao_id);
    $("rel-resumo").textContent = `Resultado para ${periodo}, em ${estacao}.`;

    $("stat-receita").textContent = Util.moeda(r.receita_total);
    $("stat-receita-detalhe").textContent = `Corridas ${Util.moeda(r.receita_corridas)} · Pacotes ${Util.moeda(r.receita_pacotes)}`;
    $("stat-corridas").textContent = String(r.total_locacoes);
    $("stat-ociosidade").textContent = Util.percentual(r.taxa_ociosidade);
    $("stat-ociosidade-detalhe").textContent = `${r.bicicletas_ociosas} de ${r.bicicletas_total} bicicletas sem corrida`;
    $("barra-ociosidade").style.width = `${Math.round(r.taxa_ociosidade * 100)}%`;
    $("stat-quebras").textContent = r.indice_quebras.toFixed(2).replace(".", ",");
    $("stat-quebras-detalhe").textContent = `${Util.plural(r.total_avarias, "avaria", "avarias")} em ${Util.plural(r.total_locacoes, "corrida", "corridas")}`;

    const total = r.receita_total;
    $("barra-corridas").style.width = total > 0 ? `${(r.receita_corridas / total) * 100}%` : "0";
    $("barra-pacotes").style.width = total > 0 ? `${(r.receita_pacotes / total) * 100}%` : "0";
    $("leg-corridas").textContent = Util.moeda(r.receita_corridas);
    $("leg-pacotes").textContent = Util.moeda(r.receita_pacotes);

    const corpo = limpar($("picos-corpo"));
    $("picos-vazio").hidden = r.horarios_pico.length > 0;
    for (const p of r.horarios_pico) {
      corpo.append(
        el(
          "tr",
          {},
          celulaTexto(p.estacao_nome),
          celulaTexto(String(p.total_locacoes)),
          celulaTexto(Util.faixaHora(p.hora_pico)),
          celulaTexto(String(p.locacoes_na_hora_pico)),
        ),
      );
    }
    $("rel-geracao").textContent = `Gerado em ${Util.dataHora(r.data_geracao)}.`;
    $("relatorio-resultado").hidden = false;
  }

  $("form-relatorio").addEventListener("submit", async (e) => {
    e.preventDefault();
    const msg = $("relatorio-msg");
    limparMsg(msg);
    const botao = e.target.querySelector('button[type="submit"]');
    const inicio = $("rel-inicio").value;
    const fim = $("rel-fim").value;
    if (inicio && fim && inicio > fim) {
      return mostrarMsg(msg, "A data inicial não pode ser depois da final.", "error");
    }
    const filtros = new URLSearchParams();
    if (inicio) filtros.set("inicio", inicio);
    if (fim) filtros.set("fim", fim);
    if ($("rel-estacao").value) filtros.set("estacao_id", $("rel-estacao").value);
    carregando(botao, true, "Gerar relatório", "Gerando...");
    const r = await api.get(`/adminweb/relatorios${filtros.toString() ? `?${filtros}` : ""}`);
    carregando(botao, false, "Gerar relatório");
    if (!r.ok) return mostrarMsg(msg, Util.erroTexto(r.data, "Não foi possível gerar o relatório."), "error");
    renderRelatorio(r.data);
  });

  // ==================================================================
  // AUDITORIA (só administrador)
  // ==================================================================
  async function carregarAuditoria() {
    if (!ehAdmin()) return;
    const r = await api.get("/adminweb/auditoria");
    if (!r.ok) return;
    const corpo = limpar($("auditoria-corpo"));
    alternarTabela("auditoria-tabela", "auditoria-vazio", r.data.length > 0);
    for (const ev of r.data) {
      corpo.append(
        el(
          "tr",
          {},
          celulaTexto(Util.dataHora(ev.data_hora)),
          celulaTexto(ev.usuario_email),
          celulaTexto(`${ev.tipo_entidade === "BICICLETA" ? "Bicicleta" : "Estação"} ${ev.entidade_id}`),
          celulaTexto(Util.rotuloAuditoria(ev.status_anterior)),
          celulaTexto(Util.rotuloAuditoria(ev.status_novo)),
        ),
      );
    }
  }
  $("btn-atualizar-auditoria").addEventListener("click", carregarAuditoria);

  // ==================================================================
  // EQUIPE (só administrador)
  // ==================================================================
  $("form-operador").addEventListener("submit", async (e) => {
    e.preventDefault();
    const msg = $("operador-msg");
    limparMsg(msg);
    const botao = e.target.querySelector(".btn");
    const corpo = {
      nome: $("op-nome").value.trim(),
      email: $("op-email").value.trim(),
      senha: $("op-password").value,
    };
    carregando(botao, true, "Cadastrar operador");
    const r = await api.post("/adminweb/operadores", corpo);
    carregando(botao, false, "Cadastrar operador");
    if (!r.ok) return mostrarMsg(msg, Util.erroTexto(r.data, "Não foi possível cadastrar o operador."), "error");
    mostrarMsg(msg, `Operador ${r.data.email} cadastrado. Ele já pode entrar nesta página.`, "success");
    e.target.reset();
  });

  // ==================================================================
  // Início
  // ==================================================================
  carregarSessao();
})();
