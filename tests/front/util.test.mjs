// Testes das funções puras do front (apresentacao/frontend/js/util.js).
// Rodar da raiz do projeto:  node --test tests/front/
import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const U = require("../../apresentacao/frontend/js/util.js");

// Intl usa espaço não separável ("R$ 10,50"); normaliza para comparar.
const semNbsp = (s) => s.replace(/ /g, " ");

test("moeda formata em reais", () => {
  assert.equal(semNbsp(U.moeda(10.5)), "R$ 10,50");
  assert.equal(semNbsp(U.moeda(0)), "R$ 0,00");
  assert.equal(semNbsp(U.moeda(1234.5)), "R$ 1.234,50");
  assert.equal(semNbsp(U.moeda("abc")), "R$ 0,00");
  assert.equal(semNbsp(U.moeda(null)), "R$ 0,00");
});

test("duracao: mm:ss e h:mm:ss", () => {
  assert.equal(U.duracao(0), "00:00");
  assert.equal(U.duracao(59), "00:59");
  assert.equal(U.duracao(754), "12:34");
  assert.equal(U.duracao(3600), "1:00:00");
  assert.equal(U.duracao(3725), "1:02:05");
  assert.equal(U.duracao(-5), "00:00");
  assert.equal(U.duracao(12.9), "00:12");
  assert.equal(U.duracao(undefined), "00:00");
});

test("plural", () => {
  assert.equal(U.plural(1, "bicicleta", "bicicletas"), "1 bicicleta");
  assert.equal(U.plural(0, "bicicleta", "bicicletas"), "0 bicicletas");
  assert.equal(U.plural(5, "bicicleta", "bicicletas"), "5 bicicletas");
});

test("distancia", () => {
  assert.equal(U.distancia(null), "");
  assert.equal(U.distancia(undefined), "");
  assert.equal(U.distancia(850.4), "850 m");
  assert.equal(U.distancia(999.6), "1000 m");
  assert.equal(U.distancia(1000), "1,0 km");
  assert.equal(U.distancia(1250), "1,3 km");
});

test("dataHora e dataCurta toleram valores inválidos", () => {
  assert.equal(U.dataHora(null), "—");
  assert.equal(U.dataHora("lixo"), "—");
  assert.equal(U.dataCurta(""), "—");
  assert.match(U.dataHora("2026-10-12T19:53:01.988864"), /12\/10\/2026|12\/10\/26/);
  assert.match(U.dataCurta("2026-10-12T19:53:01"), /12\/10\/2026/);
});

test("faixaHora", () => {
  assert.equal(U.faixaHora(8), "8h–9h");
  assert.equal(U.faixaHora(17), "17h–18h");
  assert.equal(U.faixaHora(23), "23h–0h");
  assert.equal(U.faixaHora(0), "0h–1h");
});

test("percentual", () => {
  assert.equal(U.percentual(0.25), "25%");
  assert.equal(U.percentual(1 / 3), "33%");
  assert.equal(U.percentual(1), "100%");
  assert.equal(U.percentual(0), "0%");
  assert.equal(U.percentual(undefined), "0%");
});

test("nomes", () => {
  assert.equal(U.primeiroNome("  Ana Maria Silva "), "Ana");
  assert.equal(U.primeiroNome(""), "");
  assert.equal(U.primeiroNome(null), "");
  assert.equal(U.iniciais("ana maria silva"), "AS");
  assert.equal(U.iniciais("Cid"), "C");
  assert.equal(U.iniciais(""), "?");
});

test("erroTexto lê os formatos de erro da API", () => {
  assert.equal(U.erroTexto({ detail: "CPF inválido" }), "CPF inválido");
  assert.equal(
    U.erroTexto({
      detail: "Há campos obrigatórios vazios ou preenchidos incorretamente.",
      erros: [
        { campo: "nome", mensagem: "Field required" },
        { campo: "senha", mensagem: "curta" },
      ],
    }),
    "nome: Field required; senha: curta",
  );
  assert.equal(U.erroTexto({ detail: [{ msg: "a" }, { msg: "b" }] }), "a; b");
  assert.equal(U.erroTexto(null, "padrão"), "padrão");
  assert.equal(U.erroTexto({}, "padrão"), "padrão");
  assert.equal(U.erroTexto({ detail: "" }, "padrão"), "padrão");
  assert.equal(U.erroTexto(undefined), "Algo deu errado. Tente novamente.");
});

test("normalizarQr aceita código puro ou URL", () => {
  assert.equal(U.normalizarQr("BIKE-ABC123"), "BIKE-ABC123");
  assert.equal(U.normalizarQr("  BIKE-ABC123\n"), "BIKE-ABC123");
  assert.equal(U.normalizarQr("https://rota.app/b?qr=BIKE-XYZ"), "BIKE-XYZ");
  assert.equal(U.normalizarQr("https://rota.app/b?codigo=BIKE-XYZ"), "BIKE-XYZ");
  assert.equal(U.normalizarQr("https://rota.app/bicicleta/BIKE-777"), "BIKE-777");
  assert.equal(U.normalizarQr(""), "");
  assert.equal(U.normalizarQr(null), "");
});

test("rotuloTipoCartao", () => {
  for (const v of ["credito", "crédito", "CARTAO_CREDITO"]) assert.equal(U.rotuloTipoCartao(v), "Crédito");
  for (const v of ["debito", "débito", "CARTAO_DEBITO"]) assert.equal(U.rotuloTipoCartao(v), "Débito");
  assert.equal(U.rotuloTipoCartao(undefined), "");
  assert.equal(U.rotuloTipoCartao("pix"), "");
});

test("rotulos e tons de status", () => {
  assert.equal(U.rotuloStatus("DISPONIVEL"), "Disponível");
  assert.equal(U.rotuloStatus("EM_MANUTENCAO"), "Em manutenção");
  assert.equal(U.rotuloStatus("OPERACIONAL"), "Operacional");
  assert.equal(U.rotuloStatus("RESOLVIDO"), "Resolvida");
  assert.equal(U.rotuloStatus("APROVADO"), "Aprovado");
  assert.equal(U.rotuloStatus("OUTRO"), "OUTRO");
  assert.equal(U.tomDoStatus("DISPONIVEL"), "ok");
  assert.equal(U.tomDoStatus("EM_MANUTENCAO"), "warn");
  assert.equal(U.tomDoStatus("BLOQUEADA"), "off");
  assert.equal(U.tomDoStatus("RECUSADO"), "off");
  assert.equal(U.tomDoStatus("EM_USO"), "info");
  assert.equal(U.tomDoStatus("???"), "info");
});

test("rotuloAuditoria preserva o aviso de agendamento", () => {
  assert.equal(U.rotuloAuditoria("DISPONIVEL"), "Disponível");
  assert.equal(U.rotuloAuditoria("EM_MANUTENCAO (agendado)"), "Em manutenção (agendado)");
  assert.equal(U.rotuloAuditoria(""), "");
});

test("diasRestantes", () => {
  const agora = "2026-10-12T12:00:00";
  assert.equal(U.diasRestantes("2026-10-19T12:00:00", agora), 7);
  assert.equal(U.diasRestantes("2026-10-12T13:00:00", agora), 1);
  assert.equal(U.diasRestantes("2026-10-01T12:00:00", agora), 0);
  assert.equal(U.diasRestantes("lixo", agora), 0);
});

test("estacoesParaDevolver filtra e ordena por distância", () => {
  const lista = [
    { id: 1, nome: "Longe", status: "OPERACIONAL", vagas_livres: 3, distancia_metros: 900 },
    { id: 2, nome: "Perto", status: "OPERACIONAL", vagas_livres: 1, distancia_metros: 100 },
    { id: 3, nome: "Lotada", status: "OPERACIONAL", vagas_livres: 0, distancia_metros: 50 },
    { id: 4, nome: "Bloqueada", status: "BLOQUEADA", vagas_livres: 5, distancia_metros: 10 },
    { id: 5, nome: "Sem GPS B", status: "OPERACIONAL", vagas_livres: 2, distancia_metros: null },
    { id: 6, nome: "Sem GPS A", status: "OPERACIONAL", vagas_livres: 2, distancia_metros: null },
  ];
  assert.deepEqual(U.estacoesParaDevolver(lista).map((e) => e.id), [2, 1, 6, 5]);
  assert.deepEqual(U.estacoesParaDevolver(null), []);
});

test("tomDoPino", () => {
  assert.equal(U.tomDoPino({ status: "OPERACIONAL", bicicletas_disponiveis: 3 }), "ok");
  assert.equal(U.tomDoPino({ status: "OPERACIONAL", bicicletas_disponiveis: 0 }), "warn");
  assert.equal(U.tomDoPino({ status: "BLOQUEADA", bicicletas_disponiveis: 3 }), "off");
});
