/* Pagina principal do Painel do Trader.
   Cada bloco le o seu proprio JSON de site/data/ e se vira sozinho:
   se um arquivo falhar, os outros blocos continuam funcionando. */

import { fmt, parsePreco, carregar, marcarBloco, aviso, semDado } from "./comum.js";

const $ = (id) => document.getElementById(id);

/* Quais blocos ainda sao exemplo. O aviso do topo sai daqui. */
const situacao = { exemplo: [], real: [] };
function registrar(nome, dados, idDoBloco) {
  if (!dados) return;
  situacao[dados.exemplo || dados.desatualizado ? "exemplo" : "real"].push(nome);
  marcarBloco(dados, idDoBloco);
}

/* ---------------- 4.1 Placar dos indicadores ---------------- */
async function placar() {
  const d = await carregar("placar");
  if (!d) return semDado($("pre"), "o placar");
  registrar("placar", d, "pre");
  const num = $("placar-num");
  num.textContent = `${d.favoraveis} de ${d.total}`;
  num.className = "bias-big " + (d.favoraveis > d.total / 2 ? "up" : "down");
  const medidor = $("meter");
  medidor.innerHTML = "";
  for (let i = 0; i < d.total; i++) {
    const s = document.createElement("span");
    if (i < d.favoraveis) s.className = "on";
    medidor.appendChild(s);
  }
  medidor.setAttribute("aria-label", `${d.favoraveis} de ${d.total} indicadores a favor da alta`);
}

/* ---------------- 4.2 Resumo do dia ---------------- */
async function resumo() {
  const d = await carregar("resumo");
  const ul = $("resumo-lista");
  if (!d) return semDado(ul.parentElement, "o resumo do dia");
  registrar("resumo", d, "bloco-resumo");
  ul.innerHTML = d.linhas.map((l) => `<li>${l}</li>`).join("");
}

/* ---------------- 4.3 O que mexe hoje ---------------- */
async function globais() {
  const d = await carregar("globais");
  const alvo = $("tiles");
  if (!d) return semDado(alvo, "os mercados globais");
  registrar("globais", d, "globais");
  alvo.innerHTML = d.ativos
    .map((a) => {
      const neg = a.variacao < 0;
      const v = a.unidade === "bps"
        ? `${fmt(Math.abs(a.variacao))} bps`
        : `${fmt(Math.abs(a.variacao), 2)}%`;
      /* Quando o papel é um substituto (SPY no lugar do futuro do S&P),
         a tela diz isso. O nome mostrado é sempre o do papel de verdade. */
      const nota = a.substitui ? `<span class="w">no lugar de ${a.substitui}</span>` : "";
      const inv = a.inverte ? `<span class="w">queda favorece a bolsa</span>` : "";
      return `<div class="tile"><span class="name">${a.nome}</span>
        <span class="val num">${a.valor}</span>
        <span class="chg num ${neg ? "down" : "up"}">${neg ? "▼" : "▲"} ${v}</span>
        <span class="w">peso ${a.peso}</span>${nota}${inv}</div>`;
    })
    .join("");
}

/* ---------------- 4.4 Termometro do mercado ---------------- */
const corZona = (v) => (v < 45 ? "var(--down)" : v > 55 ? "var(--up)" : "var(--muted)");
const nomeZona = (v) =>
  v < 25 ? "Medo extremo" : v < 45 ? "Medo" : v <= 55 ? "Neutro" : v <= 75 ? "Ganância" : "Ganância extrema";

async function termometro() {
  const d = await carregar("termometro");
  if (!d) return semDado($("bloco-termometro"), "o termômetro");
  registrar("termômetro", d, "bloco-termometro");

  $("comps").innerHTML = d.componentes
    .map(
      (c) =>
        `<li><span>${c.nome}</span><span class="cbar"><i style="width:${c.nota}%;background:${corZona(c.nota)}"></i></span><span class="v">${c.nota}</span></li>`
    )
    .join("");

  const v = d.nota;
  const cx = 110, cy = 112, r = 92, sw = 16;
  const pt = (n, rr) => {
    const a = Math.PI * (1 - n / 100);
    return [cx + rr * Math.cos(a), cy - rr * Math.sin(a)];
  };
  const arco = (a, b, cor, op) => {
    const [x1, y1] = pt(a, r), [x2, y2] = pt(b, r);
    return `<path d="M${x1} ${y1} A${r} ${r} 0 0 1 ${x2} ${y2}" fill="none" stroke="${cor}" stroke-width="${sw}" opacity="${op}"/>`;
  };

  let s = "";
  [
    [0, 24.5, "var(--down)", 0.9],
    [25.5, 44.5, "var(--down)", 0.45],
    [45.5, 54.5, "var(--line)", 1],
    [55.5, 74.5, "var(--up)", 0.45],
    [75.5, 100, "var(--up)", 0.9],
  ].forEach((z) => (s += arco(...z)));

  const [nx, ny] = pt(v, r - 26);
  s += `<line x1="${cx}" y1="${cy}" x2="${nx}" y2="${ny}" stroke="var(--fg)" stroke-width="3" stroke-linecap="round"/><circle cx="${cx}" cy="${cy}" r="6" fill="var(--fg)"/>`;
  s += `<text x="6" y="122" font-size="10" fill="var(--muted)" font-family="IBM Plex Sans, sans-serif">Medo extremo</text><text x="214" y="122" text-anchor="end" font-size="10" fill="var(--muted)" font-family="IBM Plex Sans, sans-serif">Ganância extrema</text>`;

  const g = $("gauge");
  g.innerHTML = s;
  g.setAttribute("aria-label", `Termômetro em ${v} de 100, zona: ${nomeZona(v)}`);
  $("gval").textContent = v;
  const z = $("gzone");
  z.textContent = nomeZona(v);
  z.style.color = corZona(v);
  $("gprev").textContent = `Ontem ${d.ontem} · há 1 semana ${d.semana} · há 1 mês ${d.mes}`;
}

/* ---------------- 4.5 Tom das noticias ---------------- */
async function noticias() {
  const d = await carregar("noticias");
  if (!d) return semDado($("bloco-noticias"), "o tom das notícias");
  registrar("notícias", d, "bloco-noticias");
  $("news-saldo").textContent = d.saldo;

  const split = $("split");
  split.innerHTML =
    `<span style="flex:${d.positivas};background:var(--up)"></span>` +
    `<span style="flex:${d.neutras};background:var(--line)"></span>` +
    `<span style="flex:${d.negativas};background:var(--down)"></span>`;
  split.setAttribute("aria-label", `${d.positivas} positivas, ${d.neutras} neutras, ${d.negativas} negativas`);

  $("news-legenda").innerHTML =
    `<span><b class="up">${d.positivas}</b> positivas</span>` +
    `<span><b>${d.neutras}</b> neutras</span>` +
    `<span><b class="down">${d.negativas}</b> negativas</span>`;

  const classe = { positiva: "up", negativa: "down", neutra: "n" };
  const rotulo = { positiva: "Positiva", negativa: "Negativa", neutra: "Neutra" };
  $("heads").innerHTML = d.manchetes
    .map((m) => `<li><span class="tone ${classe[m.tom]}">${rotulo[m.tom]}</span><span>${m.titulo}</span></li>`)
    .join("");
}

/* ---------------- 4.6 Humor da comunidade ---------------- */
async function enquete() {
  const d = await carregar("enquete");
  if (!d) return semDado($("humor"), "a enquete");
  registrar("enquete", d, "humor");

  const nomes = { c: "Comprado", v: "Vendido", f: "De fora" };
  const cores = { c: "var(--up)", v: "var(--down)", f: "var(--muted)" };
  $("enquete-pergunta").textContent = d.pergunta;
  $("enquete-contraste").innerHTML =
    `Sem certo ou errado: é o retrato de como a comunidade está posicionada. <b>${d.contraste}</b>`;

  /* 1 voto por aparelho por dia, como diz a especificação. */
  const hoje = new Date().toISOString().slice(0, 10);
  let meu = null;
  try {
    const guardado = JSON.parse(localStorage.getItem("humor-voto") || "null");
    if (guardado && guardado.dia === hoje) meu = guardado.opcao;
  } catch (e) {
    /* navegador sem localStorage: segue sem voto guardado */
  }

  function desenhar() {
    const total = d.votos.c + d.votos.v + d.votos.f + (meu ? 1 : 0);
    $("pollres").innerHTML = ["c", "v", "f"]
      .map((k) => {
        const n = d.votos[k] + (meu === k ? 1 : 0);
        const p = Math.round((n / total) * 100);
        const seu = meu === k ? '<em class="you">seu voto</em>' : "";
        return `<li><span>${nomes[k]}${seu}</span><span class="cbar"><i style="width:${p}%;background:${cores[k]}"></i></span><span class="v">${p}%</span></li>`;
      })
      .join("");
    $("pollcount").textContent = `${fmt(total)} votos de exemplo`;
    document.querySelectorAll(".pollb").forEach((b) => {
      const on = b.dataset.o === meu;
      b.classList.toggle("on", on);
      b.setAttribute("aria-pressed", on);
    });
  }

  document.querySelectorAll(".pollb").forEach((b) =>
    b.addEventListener("click", () => {
      meu = b.dataset.o;
      try {
        localStorage.setItem("humor-voto", JSON.stringify({ dia: hoje, opcao: meu }));
      } catch (e) {
        /* sem localStorage o voto vale só nesta visita */
      }
      desenhar();
      aviso("Voto registrado neste aparelho. Na Fase 6 ele passa a contar de verdade.");
    })
  );
  desenhar();
}

/* ---------------- 4.7 Fluxo estrangeiro ---------------- */
async function fluxo() {
  const d = await carregar("fluxo");
  if (!d) return semDado($("bloco-fluxo"), "o fluxo estrangeiro");
  registrar("fluxo", d, "bloco-fluxo");

  const svg = $("flow"), W = 320, H = 150, pad = 22, meio = H / 2;
  const max = Math.max(2, ...d.pregoes.map((v) => Math.abs(v)));
  const bw = (W - pad) / d.pregoes.length;

  let g = `<line x1="${pad}" x2="${W}" y1="${meio}" y2="${meio}" stroke="var(--line)"/>`;
  [max, -max].forEach((v) => {
    const y = meio - (v / max) * (meio - 10);
    g += `<line x1="${pad}" x2="${W}" y1="${y}" y2="${y}" stroke="var(--line)" stroke-dasharray="2 4"/>`;
    g += `<text x="0" y="${y + 4}" font-size="10" fill="var(--muted)" font-family="IBM Plex Mono, monospace">${v > 0 ? "+" : "−"}${fmt(Math.abs(v), 0)}</text>`;
  });
  g += `<text x="8" y="${meio + 4}" font-size="10" fill="var(--muted)" font-family="IBM Plex Mono, monospace">0</text>`;

  d.pregoes.forEach((v, i) => {
    const h = (Math.abs(v) / max) * (meio - 10);
    const x = pad + i * bw + 2;
    const y = v >= 0 ? meio - h : meio;
    const ultimo = i === d.pregoes.length - 1;
    g += `<rect x="${x}" y="${y}" width="${bw - 4}" height="${h}" rx="1.5" fill="${v >= 0 ? "var(--up)" : "var(--down)"}" opacity="${ultimo ? 1 : 0.75}"/>`;
  });
  svg.innerHTML = g;
  svg.setAttribute(
    "aria-label",
    `Fluxo estrangeiro diário dos últimos ${d.pregoes.length} pregões, em ${d.unidade}`
  );

  const sinal = (v, c) => `<b class="num ${v >= 0 ? "up" : "down"}">${v >= 0 ? "+" : "−"}${fmt(Math.abs(v), c)}</b>`;
  $("fluxo-stats").innerHTML =
    `<span class="muted">Ontem ${sinal(d.ontem, 2)}</span>` +
    `<span class="muted">Mês ${sinal(d.mes, 1)}</span>` +
    `<span class="muted">Ano ${sinal(d.ano, 1)}</span>`;
}

/* ---------------- 4.8 Quem esta comprado no WIN ---------------- */
async function participantes() {
  const d = await carregar("participantes");
  if (!d) return semDado($("bloco-participantes"), "as posições por participante");
  registrar("participantes", d, "bloco-participantes");

  $("players").innerHTML = d.participantes
    .map((p) => {
      const sobe = p.direcao === "sobe";
      const saldo = `${p.saldo >= 0 ? "+" : "−"}${fmt(Math.abs(p.saldo))}`;
      /* seta mais texto: a cor sozinha nunca carrega a informação */
      return `<tr><td>${p.nome}</td><td class="r num">${saldo}</td><td class="r ${sobe ? "up" : "down"}">${sobe ? "▲" : "▼"} <span style="font-size:11px">${sobe ? "subiu" : "caiu"}</span></td></tr>`;
    })
    .join("");
  $("players-leitura").innerHTML = `Leitura: <b>${d.leitura}.</b>`;
}

/* ---------------- 4.9 Niveis do dia + 4.10 Calculadora ---------------- */
async function niveis() {
  const d = await carregar("niveis");
  if (!d) {
    semDado($("niveis"), "os níveis do dia");
    semDado($("calc"), "a calculadora");
    return;
  }

  registrar("níveis", d, "niveis");

  for (const chave of ["win", "wdo"]) {
    const a = d.ativos[chave], c = a.casas;
    const lo1 = a.ajuste - a.desvio, hi1 = a.ajuste + a.desvio;
    const lo2 = a.ajuste - 2 * a.desvio, hi2 = a.ajuste + 2 * a.desvio;

    $(`${chave}-titulo`).textContent = a.nome;
    $(`${chave}-venc`).textContent = `vence em ${a.dias_vencimento} dias`;
    $(`${chave}-ajuste`).textContent = fmt(a.ajuste, c);

    const gap = $(`${chave}-gap`);
    gap.textContent = `${a.gap >= 0 ? "+" : "−"}${fmt(Math.abs(a.gap), c)}${chave === "win" ? " pts" : ""}`;
    gap.className = a.gap >= 0 ? "up" : "down";

    $(`${chave}-max`).textContent = fmt(a.maxima, c);
    $(`${chave}-min`).textContent = fmt(a.minima, c);
    $(`${chave}-desvio`).textContent = `±${fmt(a.desvio, c)} pts`;
    $(`${chave}-lo`).textContent = fmt(lo1, c);
    $(`${chave}-hi`).textContent = fmt(hi1, c);
    $(`${chave}-track`).setAttribute(
      "aria-label",
      `Faixa de 1 desvio entre ${fmt(lo1, c)} e ${fmt(hi1, c)}; faixa de 2 desvios entre ${fmt(lo2, c)} e ${fmt(hi2, c)}`
    );

    /* O placar de acerto só aparece quando existe de verdade. Número de
       exemplo ao lado de volatilidade real passaria por medida aferida. */
    const partes = [];
    if (a.faixa_ampliada) partes.push(a.faixa_ampliada);
    partes.push(`2 desvios (95%): ${fmt(lo2, c)} a ${fmt(hi2, c)}`);
    if (a.acertos != null) {
      partes.push(`Faixa respeitada em ${a.acertos} dos últimos ${a.janela} pregões`);
    }
    $(`${chave}-hit`).textContent = partes.join(" · ");

    /* De onde saiu a largura da faixa. O painel sempre diz qual método usou. */
    const vol = a.volatilidade;
    const linhaVol = $(`${chave}-vol`);
    if (vol) {
      const dia = new Date(`${vol.data}T12:00:00`).toLocaleDateString("pt-BR");
      linhaVol.innerHTML =
        `Volatilidade <b>${fmt(vol.anual_pct, 1)}% ao ano</b>, ${vol.metodo}, de ${dia}. ` +
        `Fonte: ${vol.fonte}. O ajuste anterior ainda é de exemplo.` +
        (vol.citacao ? `<br><span class="muted">${vol.citacao}</span>` : "");
      linhaVol.hidden = false;
    } else {
      linhaVol.hidden = true;
    }
  }

  /* Calculadora: o usuário digita o preço que vê na plataforma dele. */
  let atual = "win";
  const campo = $("price");

  function calcular() {
    const a = d.ativos[atual], c = a.casas;
    const p = parsePreco(campo.value);
    const saida = $("calcout"), msg = $("calcmsg");

    if (!isFinite(p) || p <= 0) {
      msg.textContent = `Digite um preço, por exemplo ${a.exemplo_preco}.`;
      saida.hidden = true;
      return;
    }
    msg.textContent = "";
    saida.hidden = false;

    const dif = p - a.ajuste, z = dif / a.desvio, az = Math.abs(z);
    $("pct").textContent = `${fmt(Math.round(az * 100))}%`;
    $("mark").style.left = `${Math.min(98, Math.max(2, 50 + 23 * z))}%`;
    $("disp").textContent = `${dif >= 0 ? "+" : "−"}${fmt(Math.abs(dif), c)} pts desde o ajuste (${fmt(a.ajuste, c)})`;

    const zEl = $("zone");
    if (az <= 1) {
      zEl.textContent = "Dentro da faixa de 1 desvio";
      zEl.className = "zone z1";
    } else if (az <= 2) {
      zEl.textContent = "Entre 1 e 2 desvios";
      zEl.className = "zone z2";
    } else {
      zEl.textContent = "Além de 2 desvios · esticado";
      zEl.className = "zone z3";
    }

    const dir = dif >= 0 ? 1 : -1;
    const b1 = a.ajuste + dir * a.desvio, b2 = a.ajuste + dir * 2 * a.desvio;
    $("next").textContent =
      az < 1
        ? `Faltam ${fmt(Math.abs(b1 - p), c)} pts para a faixa de 1 desvio (${fmt(b1, c)})`
        : az < 2
        ? `Faltam ${fmt(Math.abs(b2 - p), c)} pts para a faixa de 2 desvios (${fmt(b2, c)})`
        : `Já passou ${fmt(Math.abs(p - b2), c)} pts da faixa de 2 desvios (${fmt(b2, c)})`;

    $("e-lo").textContent = fmt(a.ajuste - 2 * a.desvio, c);
    $("e-hi").textContent = fmt(a.ajuste + 2 * a.desvio, c);

    const fech = $("calc-fechamento");
    fech.innerHTML = a.fechamento ? `No fechamento: <b>${a.fechamento}.</b>` : "";
    fech.hidden = !a.fechamento;
  }

  document.querySelectorAll(".segb").forEach((b) =>
    b.addEventListener("click", () => {
      atual = b.dataset.a;
      document.querySelectorAll(".segb").forEach((x) => {
        const on = x === b;
        x.classList.toggle("on", on);
        x.setAttribute("aria-pressed", on);
      });
      campo.value = d.ativos[atual].exemplo_preco;
      calcular();
    })
  );
  campo.addEventListener("input", calcular);
  campo.value = d.ativos.win.exemplo_preco;
  calcular();
}

/* ---------------- 4.11 Agenda que move o mercado ---------------- */
async function agenda() {
  const d = await carregar("agenda");
  const alvo = $("events");
  if (!d) return semDado(alvo, "a agenda");
  registrar("agenda", d, "agenda");
  $("agenda-fuso").textContent = d.fuso;
  alvo.innerHTML = d.eventos
    .map(
      (e) =>
        `<div class="ev"><span class="t">${e.hora}</span><span>${e.evento}</span><span class="pill ${e.impacto}">${e.impacto === "alto" ? "Alto" : "Médio"}</span><span class="hist">Histórico: ${e.historico}</span></div>`
    )
    .join("");
}

/* ---------------- botoes que ainda sao demonstracao ---------------- */
function botoes() {
  $("share")?.addEventListener("click", () => aviso("Na Fase 6 isto gera a imagem do dia para compartilhar."));
  $("tg")?.addEventListener("click", () => aviso("Na Fase 6 isto abre o canal do Telegram."));
}

/* Cada bloco é independente: um erro em um não derruba os outros. */
Promise.allSettled([
  placar(), resumo(), globais(), termometro(), noticias(),
  enquete(), fluxo(), participantes(), niveis(), agenda(),
]).then(() => {
  /* Um aviso honesto sobre uma pagina mista: diz quanto ja e real e
     manda olhar o selo de cada bloco, em vez de generalizar. */
  const el = $("aviso-exemplo");
  if (!el) return;
  const nReal = situacao.real.length;
  const nExemplo = situacao.exemplo.length;
  if (nExemplo === 0 && nReal > 0) {
    el.innerHTML = "Todos os blocos desta página estão com <b>dados reais</b>.";
  } else if (nReal === 0) {
    el.innerHTML = "Esta página mostra <b>dados de exemplo</b>. Nenhum número é real.";
  } else {
    el.innerHTML =
      `<b>${nReal} de ${nReal + nExemplo} blocos</b> já estão com dados reais ` +
      `(${situacao.real.join(", ")}). Os demais ainda são exemplo e estão marcados ` +
      `com o selo <span class="tag-exemplo" style="margin:0">exemplo</span>.`;
  }
  el.hidden = false;
});
botoes();
