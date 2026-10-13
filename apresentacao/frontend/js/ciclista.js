/*
 * js/ciclista.js
 * ----------------------------------------------------------------
 * Site do ciclista (index.html): entrada, estações e mapa (C6), corrida
 * com QR Code, cronômetro e devolução (B8), pagamentos e pacotes (C6).
 * Depende de js/util.js e js/app.js.
 */
(function () {
  "use strict";

  const { $, el, limpar, selo, mostrarMsg, limparMsg, toast, carregando } = App;
  const api = App.criarCliente("rota_access_token");
  const dormir = (ms) => new Promise((r) => setTimeout(r, ms));

  const estado = {
    usuario: null,
    estacoes: [],
    pos: null, // { lat, lng } quando o ciclista toca em "Perto de mim"
    selecionada: null,
    cartoes: [],
    corrida: null, // última resposta de /locacoes/ativa
    visao: null, // tela atual da aba Pedalar
  };
  const timers = { cronometro: 0, corrida: 0, estacoes: 0 };

  // ==================================================================
  // Entrada: abas de login/cadastro, máscaras e sessão
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

  App.ligarMascara($("reg-cpf"), "cpf");
  App.ligarMascara($("reg-telefone"), "telefone");
  App.ligarMascara($("cartao-numero"), "cartao");
  App.ligarMascara($("cartao-validade"), "validade");
  App.ligarMascara($("cartao-cvv"), "digitos");

  $("form-register").addEventListener("submit", async (e) => {
    e.preventDefault();
    const msg = $("register-msg");
    limparMsg(msg);
    const botao = e.target.querySelector(".btn");
    const corpo = {
      nome: $("reg-nome").value.trim(),
      email: $("reg-email").value.trim(),
      senha: $("reg-password").value,
      cpf: $("reg-cpf").value.trim(),
      telefone: $("reg-telefone").value.trim(),
      endereco: $("reg-endereco").value.trim() || null,
    };
    carregando(botao, true, "Criar conta");
    const r = await api.post("/webclient/register", corpo);
    carregando(botao, false, "Criar conta");
    if (!r.ok) return mostrarMsg(msg, Util.erroTexto(r.data, "Não foi possível criar a conta."), "error");
    mostrarMsg(msg, "Conta criada. Agora entre com seus dados.", "success");
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
    const r = await api.entrar("/webclient/login", $("login-email").value.trim(), $("login-password").value);
    carregando(botao, false, "Entrar");
    if (!r.ok) return mostrarMsg(msg, Util.erroTexto(r.data, "E-mail ou senha incorretos."), "error");
    api.guardarToken(r.data.access_token);
    e.target.reset();
    await carregarSessao();
  });

  async function contarEstacoesNaEntrada() {
    const r = await api.get("/webclient/estacoes");
    if (r.ok) $("hero-estacoes-count").textContent = r.data.length;
  }

  function mostrarEntradaTela() {
    pararTudo();
    $("tela-app").hidden = true;
    $("tela-auth").hidden = false;
    contarEstacoesNaEntrada();
  }

  function sair(avisar) {
    api.sair();
    estado.usuario = null;
    estado.corrida = null;
    estado.visao = null;
    estado.cartoes = [];
    if (avisar) toast("Sua sessão expirou. Entre novamente.", "error");
    mostrarEntradaTela();
    mostrarEntrada("login");
  }

  let sessaoExpirando = false;
  api.aoExpirar(() => {
    if (sessaoExpirando) return;
    sessaoExpirando = true;
    sair(true);
    setTimeout(() => (sessaoExpirando = false), 500);
  });

  $("btn-sair").addEventListener("click", () => sair(false));
  $("btn-sair-conta").addEventListener("click", () => sair(false));

  async function carregarSessao() {
    if (!api.token()) return mostrarEntradaTela();
    const r = await api.get("/webclient/me");
    if (!r.ok) {
      if (r.status !== 0) api.sair();
      return mostrarEntradaTela();
    }
    estado.usuario = r.data;
    $("tela-auth").hidden = true;
    $("tela-app").hidden = false;
    preencherConta();
    iniciarPollingEstacoes();

    const emCorrida = await verificarCorridaAtiva();
    abas.selecionar(emCorrida ? "pedalar" : "estacoes");
    carregarPagamentos();
  }

  function preencherConta() {
    const u = estado.usuario;
    $("topo-nome").textContent = Util.primeiroNome(u.nome) || u.email;
    $("conta-iniciais").textContent = Util.iniciais(u.nome || u.email);
    $("conta-nome").textContent = u.nome || "—";
    $("conta-email").textContent = u.email;
    $("conta-cpf").textContent = u.cpf || "—";
    $("conta-telefone").textContent = u.telefone || "—";
    $("conta-endereco").textContent = u.endereco || "Não informado";
  }

  function pararTudo() {
    pararCamera();
    pararCorrida();
    clearInterval(timers.estacoes);
    timers.estacoes = 0;
  }

  // ==================================================================
  // Abas do aplicativo
  // ==================================================================
  const abas = App.criarAbas(Array.from(document.querySelectorAll(".tabbar button")), {
    aoMudar(nome) {
      if (nome !== "pedalar" && estado.visao === "escaneando") {
        pararCamera();
        mostrarOcioso();
      }
      if (nome === "estacoes") {
        carregarEstacoes(true);
        setTimeout(() => mapa.mapa && mapa.mapa.invalidateSize(), 60);
      }
      if (nome === "pedalar") prepararPedalar();
      if (nome === "pagamentos") carregarPagamentos();
      window.scrollTo({ top: 0 });
    },
  });

  // ==================================================================
  // ESTAÇÕES (lista + mapa)
  // ==================================================================
  const mapa = { mapa: null, camada: null, eu: null, ajustado: false };

  async function carregarEstacoes(silencioso) {
    const consulta = estado.pos ? `?lat=${estado.pos.lat}&lng=${estado.pos.lng}` : "";
    const r = await api.get(`/webclient/estacoes${consulta}`);
    if (!r.ok) {
      if (!silencioso) mostrarMsg($("est-msg"), Util.erroTexto(r.data, "Não foi possível carregar as estações."), "error");
      return;
    }
    limparMsg($("est-msg"));
    estado.estacoes = r.data;
    renderEstacoes();
    atualizarMapa();
    if (estado.visao === "devolucao") preencherDestinos($("dev-estacao").value);
  }

  function cartaoEstacao(e) {
    const operacional = e.status === "OPERACIONAL";
    const classe = ["est-card", operacional ? "" : "indisponivel", estado.selecionada === e.id ? "selecionada" : ""]
      .filter(Boolean)
      .join(" ");
    return el(
      "button",
      { type: "button", class: classe, onclick: () => selecionarEstacao(e.id, true) },
      el(
        "div",
        { class: "info" },
        el("strong", { text: e.nome }),
        el("span", { text: e.endereco }),
        el(
          "div",
          { class: "extra" },
          operacional ? null : selo(e.status),
          e.distancia_metros != null ? el("span", { text: `${Util.distancia(e.distancia_metros)} de você` }) : null,
        ),
      ),
      operacional
        ? el(
            "div",
            { class: "numeros" },
            el("div", {}, el("b", { text: e.bicicletas_disponiveis }), el("small", { text: "bicicletas" })),
            el("div", {}, el("b", { text: e.vagas_livres }), el("small", { text: "vagas" })),
          )
        : null,
    );
  }

  function renderEstacoes() {
    const lista = limpar($("est-lista"));
    $("est-vazio").hidden = estado.estacoes.length > 0;
    for (const e of estado.estacoes) lista.append(cartaoEstacao(e));
  }

  function selecionarEstacao(id, focarMapa) {
    estado.selecionada = id;
    renderEstacoes();
    if (!focarMapa || !mapa.mapa) return;
    const e = estado.estacoes.find((x) => x.id === id);
    if (e && typeof e.latitude === "number") {
      mapa.mapa.flyTo([e.latitude, e.longitude], 16, { duration: 0.6 });
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }

  function conteudoPopup(e) {
    const operacional = e.status === "OPERACIONAL";
    return el(
      "div",
      {},
      el("strong", { text: e.nome }),
      el("br"),
      el("span", { text: e.endereco }),
      el("br"),
      el("span", {
        text: operacional
          ? `${Util.plural(e.bicicletas_disponiveis, "bicicleta pronta", "bicicletas prontas")} · ${Util.plural(e.vagas_livres, "vaga livre", "vagas livres")}`
          : Util.rotuloStatus(e.status),
      }),
    );
  }

  async function atualizarMapa() {
    const bloco = $("mapa-bloco");
    const aviso = $("mapa-aviso");
    const comCoordenadas = estado.estacoes.filter(
      (e) => typeof e.latitude === "number" && typeof e.longitude === "number",
    );
    if (!estado.estacoes.length) {
      bloco.hidden = true;
      aviso.hidden = true;
      return;
    }
    if (!comCoordenadas.length) {
      bloco.hidden = true;
      aviso.hidden = false;
      aviso.textContent =
        "O mapa aparece quando as estações têm coordenadas no sistema. A lista abaixo já mostra a disponibilidade de cada uma.";
      return;
    }

    let L;
    try {
      L = await App.bibliotecas.leaflet();
    } catch (_) {
      bloco.hidden = true;
      aviso.hidden = false;
      aviso.textContent = "Não foi possível carregar o mapa (sem internet?). A lista abaixo continua funcionando.";
      return;
    }
    bloco.hidden = false;
    aviso.hidden = true;

    if (!mapa.mapa) {
      mapa.mapa = L.map("mapa", { zoomControl: true }).setView([-27.5954, -48.548], 13);
      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "© OpenStreetMap",
      }).addTo(mapa.mapa);
      mapa.camada = L.layerGroup().addTo(mapa.mapa);
    }

    mapa.camada.clearLayers();
    for (const e of comCoordenadas) {
      const tom = Util.tomDoPino(e);
      const numero = e.status === "OPERACIONAL" ? Number(e.bicicletas_disponiveis) || 0 : "–";
      const marcador = L.marker([e.latitude, e.longitude], {
        icon: L.divIcon({
          className: "",
          html: `<div class="pino ${tom}">${numero}</div>`,
          iconSize: [34, 34],
          iconAnchor: [17, 17],
          popupAnchor: [0, -18],
        }),
        title: e.nome,
      });
      marcador.bindPopup(conteudoPopup(e));
      marcador.on("click", () => selecionarEstacao(e.id, false));
      marcador.addTo(mapa.camada);
    }

    if (mapa.eu) mapa.eu.remove();
    mapa.eu = null;
    if (estado.pos) {
      mapa.eu = L.marker([estado.pos.lat, estado.pos.lng], {
        icon: L.divIcon({ className: "", html: '<div class="pino-eu"></div>', iconSize: [18, 18], iconAnchor: [9, 9] }),
        interactive: false,
        zIndexOffset: -100,
      }).addTo(mapa.mapa);
    }

    if (!mapa.ajustado) {
      const pontos = comCoordenadas.map((e) => [e.latitude, e.longitude]);
      if (estado.pos) pontos.push([estado.pos.lat, estado.pos.lng]);
      mapa.mapa.fitBounds(pontos, { padding: [36, 36], maxZoom: 16 });
      mapa.ajustado = true;
    }
    mapa.mapa.invalidateSize();
  }

  $("btn-perto").addEventListener("click", async () => {
    const botao = $("btn-perto");
    botao.disabled = true;
    try {
      estado.pos = await App.localizar();
      mapa.ajustado = false;
      await carregarEstacoes();
      toast("Estações ordenadas pela distância.", "success");
    } catch (e) {
      toast(e.message, "error");
    } finally {
      botao.disabled = false;
    }
  });
  $("btn-atualizar-estacoes").addEventListener("click", () => carregarEstacoes());

  function iniciarPollingEstacoes() {
    clearInterval(timers.estacoes);
    timers.estacoes = setInterval(() => {
      if (!document.hidden && abas.atual() === "estacoes") carregarEstacoes(true);
    }, 20000);
  }

  // ==================================================================
  // PEDALAR (QR Code, corrida, devolução, recibo)
  // ==================================================================
  function mostrarVisao(nome) {
    for (const v of document.querySelectorAll("#aba-pedalar [data-visao]")) v.hidden = v.dataset.visao !== nome;
    estado.visao = nome;
  }

  /** Marca o passo `n` da lista `ulId` como "ativo", "feito" ou "erro". */
  function passo(ulId, n, situacao) {
    for (const li of $(ulId).querySelectorAll("li")) {
      const numero = Number(li.dataset.passo);
      const marca = li.querySelector(".marca");
      if (numero !== n) continue;
      li.className = situacao || "";
      limpar(marca);
      if (situacao === "ativo") marca.append(el("span", { class: "girando", style: "width:16px;height:16px;border-width:2px" }));
      else if (situacao === "feito") marca.textContent = "✓";
      else if (situacao === "erro") marca.textContent = "!";
      else marca.textContent = String(numero);
    }
  }
  function reiniciarPassos(ulId) {
    for (const li of $(ulId).querySelectorAll("li")) passo(ulId, Number(li.dataset.passo), "");
  }

  async function prepararPedalar() {
    const emAndamento = ["escaneando", "destravando", "corrida", "devolucao", "confirmando", "concluido"];
    if (emAndamento.includes(estado.visao)) return;
    mostrarVisao("carregando");
    if (!(await verificarCorridaAtiva())) await mostrarOcioso();
  }

  /** Há corrida no servidor? Se sim, mostra a tela da corrida. */
  async function verificarCorridaAtiva() {
    const r = await api.get("/webclient/locacoes/ativa");
    if (r.ok) {
      estado.corrida = r.data;
      mostrarCorrida();
      return true;
    }
    estado.corrida = null;
    return false;
  }

  // ---------- Pronto para pedalar ----------
  async function mostrarOcioso() {
    pararCorrida();
    pararCamera();
    limparMsg($("ocioso-msg"));
    limpar($("sugestoes-bicicletas"));
    $("form-codigo").hidden = true;
    $("codigo-manual").value = "";
    await carregarCartoes();

    const aviso = limpar($("ocioso-aviso"));
    const credito = estado.cartoes.some((c) => Util.rotuloTipoCartao(c.tipo) === "Crédito");
    if (!estado.cartoes.length) {
      aviso.append(
        el(
          "div",
          { class: "aviso erro" },
          el("p", { text: "Você precisa de um cartão de crédito vinculado para alugar uma bicicleta." }),
          el("button", { class: "btn pequeno", type: "button", text: "Cadastrar cartão", onclick: () => abas.selecionar("pagamentos") }),
        ),
      );
    } else if (!credito) {
      aviso.append(
        el(
          "div",
          { class: "aviso" },
          el("p", { text: "Você só tem cartão de débito. Para alugar é necessário um cartão de crédito." }),
          el("button", { class: "btn pequeno", type: "button", text: "Vincular crédito", onclick: () => abas.selecionar("pagamentos") }),
        ),
      );
    }
    mostrarVisao("ocioso");
  }

  function abrirDigitacao() {
    $("form-codigo").hidden = false;
    $("codigo-manual").focus();
  }
  $("btn-digitar").addEventListener("click", abrirDigitacao);
  $("btn-scan-digitar").addEventListener("click", async () => {
    pararCamera();
    await mostrarOcioso();
    abrirDigitacao();
  });
  $("btn-cancelar-scan").addEventListener("click", () => mostrarOcioso());
  $("form-codigo").addEventListener("submit", (e) => {
    e.preventDefault();
    tentarDestravar(Util.normalizarQr($("codigo-manual").value));
  });

  // ---------- Câmera e leitura do QR Code ----------
  const camera = { stream: null, timer: 0, detector: null, canvas: null, ativo: false };

  function legendaScanner(texto) {
    $("scanner-legenda").textContent = texto;
  }

  async function criarDetector() {
    if (!("BarcodeDetector" in window)) return null;
    try {
      const formatos = await window.BarcodeDetector.getSupportedFormats();
      if (!formatos.includes("qr_code")) return null;
      return new window.BarcodeDetector({ formats: ["qr_code"] });
    } catch (_) {
      return null;
    }
  }

  async function semCamera(texto) {
    pararCamera();
    await mostrarOcioso();
    mostrarMsg($("ocioso-msg"), texto, "error");
    abrirDigitacao();
  }

  async function iniciarScanner() {
    mostrarVisao("escaneando");
    legendaScanner("Abrindo a câmera…");
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      return semCamera("Este navegador não permite usar a câmera aqui. Digite o código da bicicleta.");
    }
    try {
      camera.stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" } },
        audio: false,
      });
    } catch (e) {
      const motivos = {
        NotAllowedError: "A permissão da câmera foi negada. Libere o acesso no navegador ou digite o código.",
        NotFoundError: "Nenhuma câmera encontrada neste aparelho. Digite o código da bicicleta.",
        NotReadableError: "A câmera está sendo usada por outro aplicativo. Feche-o ou digite o código.",
      };
      return semCamera(motivos[e.name] || "Não foi possível abrir a câmera. Digite o código da bicicleta.");
    }

    const video = $("camera");
    video.srcObject = camera.stream;
    try {
      await video.play();
    } catch (_) {
      /* alguns navegadores iniciam sozinhos */
    }

    camera.detector = await criarDetector();
    if (!camera.detector) {
      try {
        await App.bibliotecas.jsqr();
      } catch (_) {
        return semCamera("Não foi possível carregar o leitor de QR Code (sem internet?). Digite o código da bicicleta.");
      }
    }
    camera.ativo = true;
    legendaScanner("Aponte para o QR Code da bicicleta");
    lerQuadro();
  }
  $("btn-escanear").addEventListener("click", iniciarScanner);

  async function detectarTexto() {
    const video = $("camera");
    if (video.readyState < 2 || !video.videoWidth) return null;
    try {
      if (camera.detector) {
        const achados = await camera.detector.detect(video);
        return achados.length ? achados[0].rawValue : null;
      }
      const largura = Math.min(video.videoWidth, 640);
      const altura = Math.round((video.videoHeight * largura) / video.videoWidth);
      camera.canvas = camera.canvas || document.createElement("canvas");
      camera.canvas.width = largura;
      camera.canvas.height = altura;
      const ctx = camera.canvas.getContext("2d", { willReadFrequently: true });
      ctx.drawImage(video, 0, 0, largura, altura);
      const imagem = ctx.getImageData(0, 0, largura, altura);
      const achado = window.jsQR(imagem.data, largura, altura, { inversionAttempts: "dontInvert" });
      return achado ? achado.data : null;
    } catch (_) {
      return null;
    }
  }

  function lerQuadro() {
    if (!camera.ativo) return;
    camera.timer = setTimeout(async () => {
      const texto = await detectarTexto();
      if (!camera.ativo) return;
      if (texto) {
        pararCamera();
        tentarDestravar(Util.normalizarQr(texto));
        return;
      }
      lerQuadro();
    }, 150);
  }

  function pararCamera() {
    camera.ativo = false;
    clearTimeout(camera.timer);
    if (camera.stream) camera.stream.getTracks().forEach((t) => t.stop());
    camera.stream = null;
    const video = $("camera");
    if (video) video.srcObject = null;
  }

  // ---------- Validar o QR e destravar ----------
  function sugestoesDeBicicletas(lista) {
    const caixa = limpar($("sugestoes-bicicletas"));
    if (!lista || !lista.length) return;
    caixa.append(el("p", { class: "sub", style: "margin:0", text: "Outras bicicletas disponíveis nesta estação:" }));
    for (const b of lista) {
      const estacao = estado.estacoes.find((e) => e.id === b.estacao_id);
      caixa.append(
        el(
          "div",
          { class: "sugestao" },
          el("div", {}, el("strong", { text: `Bicicleta #${b.id}` }), el("span", { text: estacao ? estacao.nome : "" })),
          el("button", { class: "btn pequeno", type: "button", text: "Alugar esta", onclick: () => tentarDestravar(b.qr_code) }),
        ),
      );
    }
  }

  async function falhaNoQr(r) {
    await mostrarOcioso();
    const msg = $("ocioso-msg");
    if (r.status === 409 && r.data && Array.isArray(r.data.sugestoes)) {
      mostrarMsg(msg, `${r.data.detail}.`, "error");
      sugestoesDeBicicletas(r.data.sugestoes);
      return;
    }
    const texto =
      r.status === 404
        ? "QR Code não encontrado. Tente escanear novamente."
        : Util.erroTexto(r.data, "Não foi possível validar o QR Code.");
    mostrarMsg(msg, texto, "error");
  }

  async function falhaNoInicio(r) {
    const detalhe = Util.erroTexto(r.data, "");
    if (r.status === 409 && detalhe.includes("corrida em andamento")) {
      toast("Você já tem uma corrida em andamento.", "info");
      if (await verificarCorridaAtiva()) return;
    }
    await mostrarOcioso();
    const msg = $("ocioso-msg");
    if (r.status === 409 && r.data && Array.isArray(r.data.sugestoes)) {
      mostrarMsg(msg, `${r.data.detail}.`, "error");
      sugestoesDeBicicletas(r.data.sugestoes);
      return;
    }
    mostrarMsg(msg, Util.erroTexto(r.data, "Não foi possível iniciar a corrida."), "error");
  }

  async function tentarDestravar(qr) {
    if (!qr) {
      await mostrarOcioso();
      return mostrarMsg($("ocioso-msg"), "Informe o código da bicicleta.", "error");
    }
    pararCamera();
    mostrarVisao("destravando");
    reiniciarPassos("passos-inicio");
    $("destravando-sub").textContent = "Validando o QR Code…";
    passo("passos-inicio", 1, "ativo");

    const v = await api.post("/webclient/qr/validar", { qr_code: qr });
    if (!v.ok) {
      passo("passos-inicio", 1, "erro");
      await dormir(350);
      return falhaNoQr(v);
    }
    passo("passos-inicio", 1, "feito");
    passo("passos-inicio", 2, "ativo");
    $("destravando-sub").textContent = `Bicicleta #${v.data.id} encontrada. Aguardando a trava abrir…`;

    const r = await api.post("/webclient/locacoes", { qr_code: qr });
    if (!r.ok) {
      passo("passos-inicio", 2, "erro");
      await dormir(350);
      return falhaNoInicio(r);
    }
    passo("passos-inicio", 2, "feito");
    passo("passos-inicio", 3, "feito");
    $("destravando-sub").textContent = "Pode pedalar!";
    await dormir(600);
    toast("Corrida iniciada. Boa pedalada!", "success");
    await verificarCorridaAtiva();
    carregarEstacoes(true);
  }

  // ---------- Corrida em andamento ----------
  const relogio = { base: 0, desde: 0 };

  function reajustarCronometro(segundos) {
    relogio.base = segundos;
    relogio.desde = performance.now();
  }
  function tickCronometro() {
    const decorrido = (performance.now() - relogio.desde) / 1000;
    $("corrida-cronometro").textContent = Util.duracao(relogio.base + decorrido);
  }

  function atualizarDadosCorrida() {
    const c = estado.corrida;
    $("corrida-origem").textContent = c.estacao_origem_nome;
    $("corrida-bicicleta").textContent = `#${c.bicicleta_id}`;
    $("corrida-custo").textContent = Util.moeda(c.custo_estimado);
    $("corrida-pacote").textContent = c.minutos_pacote > 0 ? `${c.minutos_pacote} min` : "—";
  }

  function definirOffline(sem) {
    $("corrida-offline").hidden = !sem;
    $("ponto-vivo").classList.toggle("parado", sem);
    $("corrida-estado").textContent = sem ? "Sem conexão com o servidor" : "Corrida em andamento";
  }

  async function sincronizarCorrida() {
    if (estado.visao !== "corrida") return;
    const r = await api.get("/webclient/locacoes/ativa");
    if (r.status === 0) return definirOffline(true);
    definirOffline(false);
    if (r.status === 404) {
      pararCorrida();
      estado.corrida = null;
      await mostrarOcioso();
      return toast("Esta corrida já foi encerrada.", "info");
    }
    if (r.ok) {
      estado.corrida = r.data;
      reajustarCronometro(r.data.duracao_segundos);
      atualizarDadosCorrida();
    }
  }

  function mostrarCorrida() {
    atualizarDadosCorrida();
    definirOffline(false);
    reajustarCronometro(estado.corrida.duracao_segundos);
    tickCronometro();
    mostrarVisao("corrida");
    clearInterval(timers.cronometro);
    clearInterval(timers.corrida);
    timers.cronometro = setInterval(tickCronometro, 1000);
    timers.corrida = setInterval(sincronizarCorrida, 10000);
  }

  function pararCorrida() {
    clearInterval(timers.cronometro);
    clearInterval(timers.corrida);
    timers.cronometro = 0;
    timers.corrida = 0;
  }

  document.addEventListener("visibilitychange", () => {
    if (!document.hidden && estado.visao === "corrida") sincronizarCorrida();
  });

  // ---------- Devolução ----------
  function preencherDestinos(selecionar) {
    const opcoes = Util.estacoesParaDevolver(estado.estacoes);
    const campo = limpar($("dev-estacao"));
    for (const e of opcoes) {
      const distancia = e.distancia_metros != null ? ` · ${Util.distancia(e.distancia_metros)}` : "";
      campo.append(
        el("option", { value: String(e.id), text: `${e.nome} — ${Util.plural(e.vagas_livres, "vaga", "vagas")}${distancia}` }),
      );
    }
    if (selecionar && opcoes.some((e) => String(e.id) === String(selecionar))) campo.value = String(selecionar);
    $("btn-confirmar-devolucao").disabled = !opcoes.length;
    $("dev-dica").textContent = opcoes.length
      ? estado.pos
        ? "Da estação mais próxima para a mais distante."
        : "Dica: toque em “Perto de mim” na aba Estações para ordenar pela distância."
      : "Nenhuma estação com vaga no momento. Tente atualizar em instantes.";
  }

  function abrirDevolucao(manterCampos) {
    limparMsg($("dev-msg"));
    limpar($("dev-sugestoes"));
    preencherDestinos(manterCampos ? $("dev-estacao").value : null);
    if (!manterCampos) {
      $("dev-avaria-check").checked = false;
      $("dev-avaria-campo").hidden = true;
      $("dev-avaria").value = "";
    }
    mostrarVisao("devolucao");
  }

  $("btn-devolver").addEventListener("click", async () => {
    const botao = $("btn-devolver");
    botao.disabled = true;
    await carregarEstacoes(true);
    botao.disabled = false;
    abrirDevolucao(false);
  });
  $("btn-voltar-corrida").addEventListener("click", () => mostrarVisao("corrida"));
  $("dev-avaria-check").addEventListener("change", (e) => {
    $("dev-avaria-campo").hidden = !e.target.checked;
    if (e.target.checked) $("dev-avaria").focus();
  });

  $("form-devolucao").addEventListener("submit", (e) => {
    e.preventDefault();
    const msg = $("dev-msg");
    limparMsg(msg);
    const estacaoId = parseInt($("dev-estacao").value, 10);
    if (!estacaoId) return mostrarMsg(msg, "Escolha a estação de destino.", "error");
    const quer = $("dev-avaria-check").checked;
    const descricao = $("dev-avaria").value.trim();
    if (quer && !descricao) return mostrarMsg(msg, "Descreva o problema ou desmarque a opção.", "error");
    // descricao_avaria sempre vai no corpo (texto ou null): o servidor espera o campo
    confirmarDevolucao(estacaoId, quer ? descricao : null);
  });

  function sugestoesDeEstacoes(lista) {
    const caixa = limpar($("dev-sugestoes"));
    if (!lista || !lista.length) return;
    caixa.append(el("p", { class: "sub", style: "margin:0", text: "Estações próximas com vaga:" }));
    for (const s of lista) {
      caixa.append(
        el(
          "div",
          { class: "sugestao" },
          el("div", {}, el("strong", { text: s.nome }), el("span", { text: `${s.endereco} · ${Util.plural(s.vagas_disponiveis, "vaga", "vagas")}` })),
          el("button", { class: "btn pequeno", type: "button", text: "Devolver aqui", onclick: () => escolherDestino(s) }),
        ),
      );
    }
  }

  function escolherDestino(estacao) {
    const campo = $("dev-estacao");
    if (!Array.from(campo.options).some((o) => o.value === String(estacao.id))) {
      campo.append(el("option", { value: String(estacao.id), text: `${estacao.nome} — ${Util.plural(estacao.vagas_disponiveis, "vaga", "vagas")}` }));
    }
    campo.value = String(estacao.id);
    $("btn-confirmar-devolucao").disabled = false;
    limparMsg($("dev-msg"));
    limpar($("dev-sugestoes"));
    toast(`Destino: ${estacao.nome}`, "info");
  }

  async function falhaNaDevolucao(r) {
    const detalhe = Util.erroTexto(r.data, "");
    if (r.status === 404 && detalhe.includes("corrida")) {
      pararCorrida();
      estado.corrida = null;
      await mostrarOcioso();
      return toast("Você não tem corrida em andamento.", "info");
    }
    abrirDevolucao(true);
    const msg = $("dev-msg");
    if (r.status === 409 && r.data && Array.isArray(r.data.sugestoes)) {
      mostrarMsg(msg, `${detalhe}. Escolha outra estação.`, "error");
      sugestoesDeEstacoes(r.data.sugestoes);
      return;
    }
    if (r.status === 503) {
      return mostrarMsg(msg, `${detalhe} A corrida continua em andamento.`, "error");
    }
    mostrarMsg(msg, Util.erroTexto(r.data, "Não foi possível concluir a devolução."), "error");
  }

  async function confirmarDevolucao(estacaoId, descricaoAvaria) {
    mostrarVisao("confirmando");
    reiniciarPassos("passos-devolucao");
    passo("passos-devolucao", 1, "ativo");

    const r = await api.post("/webclient/locacoes/encerrar", {
      estacao_id: estacaoId,
      descricao_avaria: descricaoAvaria,
    });
    if (!r.ok) {
      passo("passos-devolucao", 1, "erro");
      await dormir(350);
      return falhaNaDevolucao(r);
    }
    passo("passos-devolucao", 1, "feito");
    passo("passos-devolucao", 2, "feito");
    passo("passos-devolucao", 3, "ativo");

    let comprovante = null;
    if (r.data.comprovante_id != null) {
      const c = await api.get(`/webclient/locacoes/${r.data.locacao_id}/comprovante`);
      if (c.ok) comprovante = c.data;
    }
    passo("passos-devolucao", 3, "feito");
    await dormir(500);

    pararCorrida();
    estado.corrida = null;
    renderConcluido(r.data, comprovante);
    mostrarVisao("concluido");
    carregarEstacoes(true);
    carregarPacotes();
  }

  // ---------- Devolução confirmada e recibo ----------
  function linhaRecibo(rotulo, valor, extra) {
    return el(
      "div",
      { class: `linha ${extra || ""}`.trim() },
      el("span", { text: rotulo }),
      valor && valor.nodeType ? valor : el("span", { text: valor }),
    );
  }

  function renderConcluido(enc, comp) {
    $("concluido-sub").textContent = `Você pedalou ${Util.plural(enc.duracao_minutos, "minuto", "minutos")}. Obrigado por pedalar com a gente.`;

    const avisos = limpar($("concluido-avisos"));
    if (enc.cobranca_pendente) {
      avisos.append(
        el(
          "div",
          { class: "aviso erro" },
          el("p", { text: `A cobrança de ${Util.moeda(enc.valor_total)} não foi concluída e ficou pendente.` }),
          el("button", { class: "btn pequeno", type: "button", text: "Ver formas de pagamento", onclick: () => abas.selecionar("pagamentos") }),
        ),
      );
    }
    if (enc.avaria_reportada) {
      avisos.append(el("div", { class: "aviso info", text: "Obrigado por avisar! A bicicleta foi bloqueada e vai para a manutenção." }));
    } else if (enc.bicicleta_em_manutencao) {
      avisos.append(el("div", { class: "aviso info", text: "Esta bicicleta foi enviada para a manutenção." }));
    }

    const recibo = limpar($("recibo"));
    if (comp) {
      recibo.append(
        linhaRecibo("Trajeto", comp.trajeto),
        linhaRecibo("Início", Util.dataHora(comp.data_hora_inicio)),
        linhaRecibo("Fim", Util.dataHora(comp.data_hora_fim)),
        linhaRecibo("Duração", `${comp.duracao_minutos} min`),
        linhaRecibo("Abatido do pacote", `${comp.minutos_pacote} min`),
        linhaRecibo("Forma de pagamento", comp.metodo_pagamento),
      );
      if (comp.pagamento_status) recibo.append(linhaRecibo("Situação", selo(comp.pagamento_status)));
      recibo.append(linhaRecibo("Total cobrado", Util.moeda(comp.tarifa_aplicada), "total"));
    } else {
      recibo.append(
        linhaRecibo("Início", Util.dataHora(enc.data_hora_inicio)),
        linhaRecibo("Fim", Util.dataHora(enc.data_hora_fim)),
        linhaRecibo("Duração", `${enc.duracao_minutos} min`),
        linhaRecibo("Abatido do pacote", `${enc.minutos_pacote} min`),
        linhaRecibo("Total cobrado", Util.moeda(enc.valor_total), "total"),
      );
    }
  }

  $("btn-nova-corrida").addEventListener("click", () => mostrarOcioso());
  $("btn-ver-estacoes").addEventListener("click", () => abas.selecionar("estacoes"));

  // ==================================================================
  // PAGAMENTOS (cartões e pacotes de minutos)
  // ==================================================================
  async function carregarCartoes() {
    const r = await api.get("/webclient/pagamentos");
    if (r.ok) {
      estado.cartoes = r.data;
      renderCartoes();
    }
    return r.ok;
  }

  function renderCartoes() {
    const lista = limpar($("cartoes-lista"));
    $("cartoes-vazio").hidden = estado.cartoes.length > 0;
    for (const c of estado.cartoes) {
      const partes = [c.bandeira, Util.rotuloTipoCartao(c.tipo), c.apelido].filter(Boolean);
      const botao = el("button", {
        class: "cartao-remover",
        type: "button",
        text: "Remover",
        "aria-label": `Remover cartão final ${c.ultimos_digitos}`,
      });
      botao.addEventListener("click", () => removerCartao(c.token, botao));
      lista.append(
        el(
          "div",
          { class: "cartao-visual" },
          el("div", { class: "bandeira", text: partes.join(" · ") }),
          el("div", { class: "numero", text: `•••• •••• •••• ${c.ultimos_digitos}` }),
          el("div", { class: "rodape" }, el("span", { text: c.nome_titular }), el("span", { text: c.validade })),
          botao,
        ),
      );
    }
  }

  async function removerCartao(token, botao) {
    if (!confirm("Remover este cartão?")) return;
    const msg = $("cartao-msg");
    limparMsg(msg);
    botao.disabled = true;
    botao.textContent = "Removendo...";
    const r = await api.delete(`/webclient/pagamentos/${encodeURIComponent(token)}`);
    if (!r.ok) {
      botao.disabled = false;
      botao.textContent = "Remover";
      return mostrarMsg(msg, Util.erroTexto(r.data, "Não foi possível remover o cartão."), "error");
    }
    mostrarMsg(msg, "Cartão removido.", "success");
    await carregarCartoes();
  }

  $("form-cartao").addEventListener("submit", async (e) => {
    e.preventDefault();
    const msg = $("cartao-msg");
    limparMsg(msg);
    const botao = e.target.querySelector(".btn");
    const tipo = $("cartao-tipo").value;
    if (!tipo) return mostrarMsg(msg, "Selecione crédito ou débito.", "error");
    const corpo = {
      tipo,
      numero_cartao: $("cartao-numero").value.replace(/\s/g, ""),
      nome_titular: $("cartao-nome").value.trim(),
      validade: $("cartao-validade").value.trim(),
      cvv: $("cartao-cvv").value.trim(),
      apelido: $("cartao-apelido").value.trim() || null,
    };
    carregando(botao, true, "Vincular cartão");
    const r = await api.post("/webclient/pagamentos", corpo);
    carregando(botao, false, "Vincular cartão");
    if (!r.ok) return mostrarMsg(msg, Util.erroTexto(r.data, "Não foi possível vincular o cartão."), "error");
    mostrarMsg(msg, "Cartão vinculado com sucesso.", "success");
    e.target.reset();
    await carregarCartoes();
  });

  // ---------- Pacotes ----------
  function pacoteVigente(p, agora) {
    return p.ativo && new Date(p.data_validade).getTime() > agora;
  }

  /** ativo | esgotado | vencido | recusado (compra não aprovada). */
  function estadoPacote(p, agora) {
    if (pacoteVigente(p, agora)) return "ativo";
    if (new Date(p.data_validade).getTime() <= agora) return "vencido";
    return p.minutos_restantes <= 0 ? "esgotado" : "recusado";
  }

  const SELO_PACOTE = {
    ativo: () => selo("DISPONIVEL", "Ativo"),
    esgotado: () => selo("PENDENTE", "Esgotado"),
    vencido: () => selo("BLOQUEADA", "Vencido"),
    recusado: () => selo("BLOQUEADA", "Pagamento recusado"),
  };

  function renderCatalogo(itens) {
    const grade = limpar($("catalogo-pacotes"));
    for (const item of itens) {
      const botao = el("button", { class: "btn pequeno", type: "button", text: "Comprar" });
      botao.addEventListener("click", () => comprarPacote(item, botao));
      grade.append(
        el(
          "div",
          { class: "pacote-oferta" },
          el("div", { class: "minutos", text: `${item.minutos} min` }),
          el("div", { class: "preco", text: Util.moeda(item.preco) }),
          el("small", { text: `válido por ${Util.plural(item.validade_dias, "dia", "dias")}` }),
          botao,
        ),
      );
    }
  }

  function renderMeusPacotes(pacotes) {
    const agora = Date.now();
    const lista = limpar($("meus-pacotes"));
    $("pacotes-vazio").hidden = pacotes.length > 0;
    const saldo = pacotes.filter((p) => pacoteVigente(p, agora)).reduce((soma, p) => soma + p.minutos_restantes, 0);
    $("saldo-pacotes").textContent = String(saldo);

    const ordenados = [...pacotes].sort((a, b) => new Date(b.data_validade) - new Date(a.data_validade));
    for (const p of ordenados) {
      const situacao = estadoPacote(p, agora);
      const ativo = situacao === "ativo";
      const restante = p.minutos_totais ? Math.max(0, Math.min(100, (p.minutos_restantes / p.minutos_totais) * 100)) : 0;
      const dias = Util.diasRestantes(p.data_validade);
      lista.append(
        el(
          "div",
          { class: "pacote-meu" },
          el(
            "div",
            { class: "topo" },
            el("strong", { text: situacao === "recusado" ? `Pacote de ${p.minutos_totais} min` : `${p.minutos_restantes} de ${p.minutos_totais} min` }),
            SELO_PACOTE[situacao](),
          ),
          ativo ? el("div", { class: "barra" }, el("i", { style: `width:${restante}%` })) : null,
          el("small", {
            class: "opcional",
            style: "display:block; margin-top:6px",
            text: ativo
              ? `Vence em ${Util.dataCurta(p.data_validade)} (${Util.plural(dias, "dia", "dias")})`
              : situacao === "recusado"
                ? "O pagamento não foi aprovado e nenhum minuto foi creditado."
                : `Validade: ${Util.dataCurta(p.data_validade)}`,
          }),
        ),
      );
    }
  }

  async function carregarPacotes() {
    const [catalogo, meus] = await Promise.all([api.get("/webclient/pacotes/catalogo"), api.get("/webclient/pacotes")]);
    if (catalogo.ok) renderCatalogo(catalogo.data);
    if (meus.ok) renderMeusPacotes(meus.data);
  }

  async function comprarPacote(item, botao) {
    if (!confirm(`Comprar ${item.minutos} minutos por ${Util.moeda(item.preco)} no seu cartão de crédito?`)) return;
    const msg = $("pacote-msg");
    limparMsg(msg);
    botao.disabled = true;
    botao.textContent = "Comprando...";
    const r = await api.post("/webclient/pacotes", { item_id: item.id });
    botao.disabled = false;
    botao.textContent = "Comprar";
    if (!r.ok) return mostrarMsg(msg, Util.erroTexto(r.data, "Não foi possível comprar o pacote."), "error");
    if (r.data.pagamento_status === "APROVADO") {
      mostrarMsg(msg, `Pacote de ${item.minutos} minutos comprado. Os minutos já estão disponíveis.`, "success");
    } else {
      mostrarMsg(msg, "Pagamento recusado. Nenhum minuto foi creditado.", "error");
    }
    await carregarPacotes();
  }

  async function carregarPagamentos() {
    await Promise.all([carregarCartoes(), carregarPacotes()]);
  }

  // ==================================================================
  // Início
  // ==================================================================
  carregarSessao();
})();
