/*
 * js/util.js
 * ----------------------------------------------------------------
 * Funções puras do front (formatação, rótulos, leitura de erros e do
 * QR Code). Não mexem no DOM: por isso rodam também no Node e têm
 * testes em tests/front/util.test.mjs.
 */
(function (raiz, fabrica) {
  if (typeof module === "object" && module.exports) module.exports = fabrica();
  else raiz.Util = fabrica();
})(typeof self !== "undefined" ? self : this, function () {
  const dois = (n) => String(n).padStart(2, "0");

  /** 10.5 -> "R$ 10,50" */
  function moeda(valor) {
    return new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency: "BRL",
    }).format(Number(valor) || 0);
  }

  /** 754 -> "12:34"; 3725 -> "1:02:05" */
  function duracao(segundos) {
    const total = Math.max(0, Math.floor(Number(segundos) || 0));
    const h = Math.floor(total / 3600);
    const m = Math.floor((total % 3600) / 60);
    const s = total % 60;
    return h > 0 ? `${h}:${dois(m)}:${dois(s)}` : `${dois(m)}:${dois(s)}`;
  }

  /** plural(1, "bicicleta", "bicicletas") -> "1 bicicleta" */
  function plural(n, um, varios) {
    return `${n} ${n === 1 ? um : varios}`;
  }

  /** 850 -> "850 m"; 1250 -> "1,3 km"; null -> "" */
  function distancia(metros) {
    if (metros == null || Number.isNaN(Number(metros))) return "";
    const m = Number(metros);
    if (m < 1000) return `${Math.round(m)} m`;
    return `${(m / 1000).toFixed(1).replace(".", ",")} km`;
  }

  /** Data e hora curtas em pt-BR; valor inválido vira "—". */
  function dataHora(iso) {
    const d = new Date(iso);
    if (!iso || Number.isNaN(d.getTime())) return "—";
    return d.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
  }

  function dataCurta(iso) {
    const d = new Date(iso);
    if (!iso || Number.isNaN(d.getTime())) return "—";
    return d.toLocaleDateString("pt-BR");
  }

  /** 17 -> "17h–18h"; 23 -> "23h–0h" */
  function faixaHora(hora) {
    return `${hora}h–${(hora + 1) % 24}h`;
  }

  /** 0.3333 -> "33%"; 0.25 -> "25%" */
  function percentual(fracao) {
    return `${Math.round((Number(fracao) || 0) * 100)}%`;
  }

  function primeiroNome(nome) {
    return String(nome || "").trim().split(/\s+/)[0] || "";
  }

  function iniciais(nome) {
    const partes = String(nome || "").trim().split(/\s+/).filter(Boolean);
    if (!partes.length) return "?";
    const letras = partes.length === 1 ? partes[0][0] : partes[0][0] + partes[partes.length - 1][0];
    return letras.toUpperCase();
  }

  /**
   * Mensagem legível a partir do corpo de erro da API. Aceita o formato do
   * projeto ({detail, erros:[{campo, mensagem}]}) e o padrão do FastAPI.
   */
  function erroTexto(dados, padrao) {
    const fallback = padrao || "Algo deu errado. Tente novamente.";
    if (!dados || typeof dados !== "object") return fallback;
    if (Array.isArray(dados.erros) && dados.erros.length) {
      return dados.erros.map((e) => `${e.campo}: ${e.mensagem}`).join("; ");
    }
    if (typeof dados.detail === "string" && dados.detail) return dados.detail;
    if (Array.isArray(dados.detail) && dados.detail.length) {
      return dados.detail.map((d) => d.msg).join("; ");
    }
    return fallback;
  }

  /**
   * O que o leitor devolve vira o código da bicicleta. Aceita o código puro
   * ("BIKE-ABC123") ou uma URL que o carregue (?qr=..., ?codigo=... ou o
   * último trecho do caminho).
   */
  function normalizarQr(texto) {
    const t = String(texto == null ? "" : texto).trim();
    if (!t) return "";
    try {
      const url = new URL(t);
      for (const chave of ["qr", "qr_code", "codigo"]) {
        const valor = url.searchParams.get(chave);
        if (valor && valor.trim()) return valor.trim();
      }
      const ultimo = url.pathname.split("/").filter(Boolean).pop();
      if (ultimo) return decodeURIComponent(ultimo).trim();
    } catch (_) {
      /* não é URL: vale o texto como veio */
    }
    return t;
  }

  /** "credito" | "CARTAO_CREDITO" | "crédito" -> "Crédito"; débito idem. */
  function rotuloTipoCartao(tipo) {
    const t = String(tipo || "").toLowerCase();
    if (t.includes("cred") || t.includes("créd")) return "Crédito";
    if (t.includes("deb") || t.includes("déb")) return "Débito";
    return "";
  }

  const STATUS_BICICLETA = {
    DISPONIVEL: "Disponível",
    EM_USO: "Em uso",
    EM_MANUTENCAO: "Em manutenção",
    BLOQUEADA: "Bloqueada",
  };
  const STATUS_ESTACAO = {
    OPERACIONAL: "Operacional",
    BLOQUEADA: "Bloqueada",
    EM_MANUTENCAO: "Em manutenção",
  };
  const STATUS_AVARIA = {
    PENDENTE: "Pendente",
    EM_REPARO: "Em reparo",
    RESOLVIDO: "Resolvida",
  };
  const STATUS_PAGAMENTO = {
    PENDENTE: "Pendente",
    APROVADO: "Aprovado",
    RECUSADO: "Recusado",
  };

  /** Cor do selo (badge) para qualquer status do sistema. */
  function tomDoStatus(status) {
    switch (status) {
      case "DISPONIVEL":
      case "OPERACIONAL":
      case "APROVADO":
      case "RESOLVIDO":
        return "ok";
      case "EM_USO":
      case "EM_REPARO":
        return "info";
      case "PENDENTE":
      case "EM_MANUTENCAO":
        return "warn";
      case "BLOQUEADA":
      case "RECUSADO":
        return "off";
      default:
        return "info";
    }
  }

  /** Rótulo de qualquer status; desconhecido volta como veio. */
  function rotuloStatus(status) {
    return (
      STATUS_BICICLETA[status] ||
      STATUS_ESTACAO[status] ||
      STATUS_AVARIA[status] ||
      STATUS_PAGAMENTO[status] ||
      status
    );
  }

  /** "EM_MANUTENCAO (agendado)" -> "Em manutenção (agendado)" (auditoria). */
  function rotuloAuditoria(texto) {
    const [base, ...resto] = String(texto || "").split(" (");
    const rotulo = rotuloStatus(base);
    return resto.length ? `${rotulo} (${resto.join(" (")}` : rotulo;
  }

  /** Dias que faltam até a data (arredonda para cima; vencido = 0). */
  function diasRestantes(iso, agora) {
    const fim = new Date(iso).getTime();
    if (Number.isNaN(fim)) return 0;
    const ref = agora ? new Date(agora).getTime() : Date.now();
    return Math.max(0, Math.ceil((fim - ref) / 86400000));
  }

  /** Estações onde dá para devolver: operacionais e com vaga, mais perto primeiro. */
  function estacoesParaDevolver(estacoes) {
    return (estacoes || [])
      .filter((e) => e.status === "OPERACIONAL" && e.vagas_livres > 0)
      .sort((a, b) => {
        const da = a.distancia_metros == null ? Infinity : a.distancia_metros;
        const db = b.distancia_metros == null ? Infinity : b.distancia_metros;
        return da - db || String(a.nome).localeCompare(String(b.nome), "pt-BR");
      });
  }

  /** Classe do pino do mapa conforme a disponibilidade da estação. */
  function tomDoPino(estacao) {
    if (estacao.status !== "OPERACIONAL") return "off";
    return estacao.bicicletas_disponiveis > 0 ? "ok" : "warn";
  }

  return {
    moeda,
    duracao,
    plural,
    distancia,
    dataHora,
    dataCurta,
    faixaHora,
    percentual,
    primeiroNome,
    iniciais,
    erroTexto,
    normalizarQr,
    rotuloTipoCartao,
    rotuloStatus,
    rotuloAuditoria,
    tomDoStatus,
    diasRestantes,
    estacoesParaDevolver,
    tomDoPino,
    STATUS_BICICLETA,
    STATUS_ESTACAO,
    STATUS_AVARIA,
    STATUS_PAGAMENTO,
  };
});
