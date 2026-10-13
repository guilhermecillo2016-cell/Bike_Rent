/*
 * js/app.js
 * ----------------------------------------------------------------
 * Base compartilhada pelas duas páginas (ciclista e gestão): cliente da
 * API, pequenos componentes de interface, abas, máscaras e carregamento
 * das bibliotecas externas só quando são usadas (a tela inicial carrega
 * rápido, RNF-01).
 *
 * Depende de js/util.js (carregado antes).
 */
window.App = (function () {
  const $ = (id) => document.getElementById(id);

  // ------------------------------------------------------------------
  // DOM
  // ------------------------------------------------------------------
  /** el("div", {class:"x", text:"oi", onclick: fn}, filho1, filho2) */
  function el(tag, props, ...filhos) {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(props || {})) {
      if (v == null || v === false) continue;
      if (k === "class") n.className = v;
      else if (k === "text") n.textContent = v;
      else if (k === "style") n.style.cssText = v;
      else if (k === "dataset") Object.assign(n.dataset, v);
      else if (k.startsWith("on") && typeof v === "function") n.addEventListener(k.slice(2), v);
      else if (k.startsWith("aria-") || k === "for" || k === "role") n.setAttribute(k, v);
      else if (k in n) n[k] = v;
      else n.setAttribute(k, v);
    }
    for (const f of filhos.flat()) {
      if (f == null || f === false) continue;
      n.append(f.nodeType ? f : document.createTextNode(String(f)));
    }
    return n;
  }

  function limpar(no) {
    while (no.firstChild) no.removeChild(no.firstChild);
    return no;
  }

  /** Selo colorido para qualquer status do sistema. */
  function selo(status, texto) {
    return el("span", { class: `selo ${Util.tomDoStatus(status)}`, text: texto || Util.rotuloStatus(status) });
  }

  // ------------------------------------------------------------------
  // Mensagens
  // ------------------------------------------------------------------
  function mostrarMsg(no, texto, tipo) {
    no.textContent = texto;
    no.className = `msg show ${tipo || "error"}`;
  }
  function limparMsg(no) {
    no.textContent = "";
    no.className = "msg";
  }

  function toast(texto, tipo) {
    let caixa = $("toasts");
    if (!caixa) {
      caixa = el("div", { id: "toasts", "aria-live": "polite", role: "status" });
      document.body.append(caixa);
    }
    const t = el("div", { class: `toast ${tipo || "info"}`, text: texto });
    caixa.append(t);
    setTimeout(() => t.classList.add("sair"), 3800);
    setTimeout(() => t.remove(), 4200);
  }

  function carregando(botao, ligado, rotuloParado, rotuloOcupado) {
    botao.disabled = ligado;
    botao.textContent = ligado ? rotuloOcupado || "Enviando..." : rotuloParado;
  }

  // ------------------------------------------------------------------
  // Cliente da API
  // ------------------------------------------------------------------
  /**
   * Cada página usa uma chave de token própria (ciclista e gestão não podem
   * se sobrescrever no mesmo navegador). Toda chamada devolve
   * { ok, status, data } e nunca lança: erro de rede vira status 0.
   */
  function criarCliente(chaveToken) {
    let aoExpirar = () => {};
    const token = () => localStorage.getItem(chaveToken);

    async function pedir(metodo, caminho, opcoes) {
      const { json, form, autenticado = true } = opcoes || {};
      const cabecalhos = {};
      if (autenticado && token()) cabecalhos.Authorization = `Bearer ${token()}`;
      let corpo;
      if (json !== undefined) {
        cabecalhos["Content-Type"] = "application/json";
        corpo = JSON.stringify(json);
      } else if (form) {
        cabecalhos["Content-Type"] = "application/x-www-form-urlencoded";
        corpo = new URLSearchParams(form).toString();
      }

      let resposta;
      try {
        resposta = await fetch(caminho, { method: metodo, headers: cabecalhos, body: corpo });
      } catch (_) {
        return { ok: false, status: 0, data: { detail: "Sem conexão com o servidor." } };
      }
      let dados = null;
      if (resposta.status !== 204) {
        try {
          dados = await resposta.json();
        } catch (_) {
          dados = null;
        }
      }
      if (resposta.status === 401 && autenticado) aoExpirar();
      return { ok: resposta.ok, status: resposta.status, data: dados };
    }

    return {
      token,
      guardarToken: (t) => localStorage.setItem(chaveToken, t),
      sair: () => localStorage.removeItem(chaveToken),
      aoExpirar: (fn) => (aoExpirar = fn),
      get: (c) => pedir("GET", c),
      post: (c, json) => pedir("POST", c, { json }),
      patch: (c, json) => pedir("PATCH", c, { json: json === undefined ? {} : json }),
      delete: (c) => pedir("DELETE", c),
      entrar: (c, email, senha) =>
        pedir("POST", c, { form: { username: email, password: senha }, autenticado: false }),
      cadastrar: (c, json, cabecalhosExtra) => pedirComCabecalho(c, json, cabecalhosExtra),
    };

    // cadastro de administrador manda a chave secreta num cabeçalho
    async function pedirComCabecalho(caminho, json, extra) {
      let resposta;
      try {
        resposta = await fetch(caminho, {
          method: "POST",
          headers: { "Content-Type": "application/json", ...(extra || {}) },
          body: JSON.stringify(json),
        });
      } catch (_) {
        return { ok: false, status: 0, data: { detail: "Sem conexão com o servidor." } };
      }
      let dados = null;
      try {
        dados = await resposta.json();
      } catch (_) {
        dados = null;
      }
      return { ok: resposta.ok, status: resposta.status, data: dados };
    }
  }

  // ------------------------------------------------------------------
  // Abas
  // ------------------------------------------------------------------
  /**
   * botoes: elementos com data-aba="nome"; painéis: ids "aba-nome".
   * Devolve { selecionar(nome), atual() }.
   */
  function criarAbas(botoes, { aoMudar } = {}) {
    let atual = null;
    function selecionar(nome) {
      for (const b of botoes) {
        const ativa = b.dataset.aba === nome;
        b.setAttribute("aria-selected", String(ativa));
        const painel = $(`aba-${b.dataset.aba}`);
        if (painel) painel.hidden = !ativa;
      }
      atual = nome;
      if (aoMudar) aoMudar(nome);
    }
    for (const b of botoes) b.addEventListener("click", () => selecionar(b.dataset.aba));
    return { selecionar, atual: () => atual };
  }

  // ------------------------------------------------------------------
  // Máscaras de entrada
  // ------------------------------------------------------------------
  const mascaras = {
    cpf(v) {
      return v
        .replace(/\D/g, "")
        .slice(0, 11)
        .replace(/(\d{3})(\d)/, "$1.$2")
        .replace(/(\d{3})(\d)/, "$1.$2")
        .replace(/(\d{3})(\d{1,2})$/, "$1-$2");
    },
    telefone(v) {
      const d = v.replace(/\D/g, "").slice(0, 11);
      if (d.length > 10) return d.replace(/(\d{2})(\d{5})(\d{4})/, "($1) $2-$3");
      if (d.length > 5) return d.replace(/(\d{2})(\d{4})(\d{0,4})/, "($1) $2-$3");
      if (d.length > 2) return d.replace(/(\d{2})(\d{0,5})/, "($1) $2");
      return d ? `(${d}` : "";
    },
    cartao(v) {
      return v.replace(/\D/g, "").slice(0, 16).replace(/(\d{4})(?=\d)/g, "$1 ");
    },
    validade(v) {
      const d = v.replace(/\D/g, "").slice(0, 4);
      return d.length > 2 ? `${d.slice(0, 2)}/${d.slice(2)}` : d;
    },
    digitos(v) {
      return v.replace(/\D/g, "").slice(0, 4);
    },
  };
  function ligarMascara(input, nome) {
    if (input) input.addEventListener("input", () => (input.value = mascaras[nome](input.value)));
  }

  // ------------------------------------------------------------------
  // Bibliotecas externas (carregadas na primeira vez que são usadas)
  // Versões travadas com SRI: se o arquivo mudar, o navegador recusa.
  // ------------------------------------------------------------------
  const pendentes = {};
  function carregarScript(url, integridade) {
    if (!pendentes[url]) {
      pendentes[url] = new Promise((resolve, reject) => {
        const s = document.createElement("script");
        s.src = url;
        if (integridade) {
          s.integrity = integridade;
          s.crossOrigin = "anonymous";
        }
        s.onload = resolve;
        s.onerror = () => {
          delete pendentes[url];
          reject(new Error(`Não foi possível carregar ${url}`));
        };
        document.head.append(s);
      });
    }
    return pendentes[url];
  }
  function carregarCss(url, integridade) {
    if (document.querySelector(`link[href="${url}"]`)) return;
    const l = document.createElement("link");
    l.rel = "stylesheet";
    l.href = url;
    if (integridade) {
      l.integrity = integridade;
      l.crossOrigin = "anonymous";
    }
    document.head.append(l);
  }

  const bibliotecas = {
    async leaflet() {
      carregarCss(
        "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css",
        "sha384-c6Rcwz4e4CITMbu/NBmnNS8yN2sC3cUElMEMfP3vqqKFp7GOYaaBBCqmaWBjmkjb",
      );
      await carregarScript(
        "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js",
        "sha384-NElt3Op+9NBMCYaef5HxeJmU4Xeard/Lku8ek6hoPTvYkQPh3zLIrJP7KiRocsxO",
      );
      return window.L;
    },
    async jsqr() {
      await carregarScript(
        "https://cdn.jsdelivr.net/npm/jsqr@1.4.0/dist/jsQR.js",
        "sha384-b5Ya4Bq3qCyz39m2ISh+4DxjAIljdeFwK/BsXLuj9gugaNwAcj/ia15fxNZL9Nlx",
      );
      return window.jsQR;
    },
    async qrcode() {
      await carregarScript(
        "https://cdnjs.cloudflare.com/ajax/libs/qrcode-generator/1.4.4/qrcode.min.js",
        "sha384-mZT2gIty7ZDdOGkxfP6joZcYdMW1Jvj9dRlfpTmaJAKKXTqzygtB22k7FLe+KZC1",
      );
      return window.qrcode;
    },
  };

  /** Posição do aparelho (promessa; recusa com texto em português). */
  function localizar() {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) return reject(new Error("Este navegador não informa a localização."));
      navigator.geolocation.getCurrentPosition(
        (p) => resolve({ lat: p.coords.latitude, lng: p.coords.longitude }),
        (e) =>
          reject(
            new Error(
              e.code === 1
                ? "Permissão de localização negada."
                : "Não foi possível obter a sua localização.",
            ),
          ),
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 30000 },
      );
    });
  }

  return {
    $,
    el,
    limpar,
    selo,
    mostrarMsg,
    limparMsg,
    toast,
    carregando,
    criarCliente,
    criarAbas,
    mascaras,
    ligarMascara,
    bibliotecas,
    localizar,
  };
})();
