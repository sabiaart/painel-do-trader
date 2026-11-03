/* Pagina /opcoes: contratos em aberto e GEX das opcoes de BOVA11.
   Os calculos sao os mesmos do prototipo, agora lendo site/data/opcoes.json.

   Atencao (pendencia da secao 10 da especificacao): ainda falta confirmar se o
   open interest do arquivo da B3 vem por opcao ou por lote. Se vier por lote,
   o GEX precisa de um multiplicador aqui. O campo "unidade_oi" do JSON existe
   para registrar isso. */

import { fmt, carregar, marcarOrigem, semDado } from "./comum.js";

const $ = (id) => document.getElementById(id);

/* densidade da normal padrao */
const npdf = (x) => Math.exp((-x * x) / 2) / Math.sqrt(2 * Math.PI);

async function montar() {
  const d = await carregar("opcoes");
  if (!d) return semDado($("bloco-gex"), "os dados de opções");
  marcarOrigem(d);

  const S = d.preco, T = d.prazo_anos, iv = d.vol_implicita, r = d.juros;
  const linhas = d.strikes;

  $("gx-titulo").textContent = `Opções de ${d.ativo} · vencimento mensal`;
  $("gx-sub").textContent = `vence ${d.vencimento} · ${d.referencia}`;

  /* gamma de Black-Scholes */
  const gamma = (preco, K) => {
    const vt = iv * Math.sqrt(T);
    const d1 = (Math.log(preco / K) + (r + (iv * iv) / 2) * T) / vt;
    return npdf(d1) / (preco * vt);
  };

  /* GEX(strike) = (OI_call - OI_put) x gamma x S^2 x 0,01 */
  const gexEm = (preco, K, call, put) => (call - put) * gamma(preco, K) * preco * preco * 0.01;
  const gexTotal = (preco) => linhas.reduce((a, l) => a + gexEm(preco, l.strike, l.call_oi, l.put_oi), 0);

  /* call wall e put wall: maior OI x gamma */
  const maiorPor = (campo) =>
    linhas.reduce((melhor, l) =>
      l[campo] * gamma(S, l.strike) > melhor[campo] * gamma(S, melhor.strike) ? l : melhor
    ).strike;
  const cw = maiorPor("call_oi");
  const pw = maiorPor("put_oi");

  /* gamma flip: onde o GEX total troca de sinal, mais perto do preco atual */
  let flip = null;
  {
    let menorDistancia = Infinity;
    let anterior = gexTotal(110);
    for (let s = 110.05; s <= 140; s += 0.05) {
      const v = gexTotal(s);
      if (anterior < 0 !== v < 0 && Math.abs(s - S) < menorDistancia) {
        menorDistancia = Math.abs(s - S);
        flip = s;
      }
      anterior = v;
    }
  }

  const total = gexTotal(S);

  /* os quatro numeros do topo */
  /* A conversão para pontos do Ibovespa só existe se soubermos o nível do
     índice. Sem ela, mostra o strike em reais e pronto - melhor do que
     multiplicar por um número inventado. */
  const emPontos = (v) =>
    d.razao_ibov ? `≈ ${fmt(Math.round(v * d.razao_ibov))} pts · ` : "";
  const cartao = (nome, valor, nota) =>
    `<div class="gx-stat"><span>${nome}</span><b>${valor == null ? "—" : fmt(valor, valor % 1 ? 2 : 0)}</b><small>${valor == null ? nota : `${emPontos(valor)}${nota}`}</small></div>`;

  const leituraTotal = total >= 0
    ? "gamma positivo: oscilação tende a ser amortecida"
    : "gamma negativo: oscilação tende a ser ampliada";

  $("gxstats").innerHTML =
    cartao("Call wall", cw, "maior gamma de calls") +
    cartao("Put wall", pw, "maior gamma de puts") +
    cartao("Gamma flip", flip, "onde o GEX troca de sinal") +
    `<div class="gx-stat"><span>GEX total</span><b class="${total >= 0 ? "up" : "down"}">${total >= 0 ? "+" : "−"}R$ ${fmt(Math.abs(total) / 1e6, 1)} mi</b><small>por 1% de variação · ${leituraTotal}</small></div>`;

  const conversao = d.razao_ibov
    ? `Níveis convertidos para pontos do Ibovespa pela relação do dia (${d.ativo} × ${fmt(d.razao_ibov)}). `
    : `Níveis em reais de ${d.ativo}: não temos o nível do Ibovespa de fonte livre para converter em pontos. `;
  const sobreVol = d.vol_fonte
    ? `<br>Gamma calculado com <b>uma volatilidade só para todos os strikes</b> (${d.vol_fonte}), ` +
      `e não com a implícita de cada série. Isso achata o sorriso de volatilidade e subestima o gamma das pontas. `
    : "";
  /* Quando parte das séries não tem strike no cadastro da B3, o gráfico
     mostra menos posição do que existe. Dizer quanto é o mínimo. */
  const buraco =
    d.cobertura_pct != null && d.cobertura_pct < 99
      ? `<br><b>O gráfico cobre ${fmt(d.cobertura_pct, 1)}% das posições em aberto.</b> ` +
        `${fmt(d.series_sem_cadastro)} séries (${fmt(d.posicoes_sem_cadastro)} contratos) ficaram de fora ` +
        `porque o cadastro da B3 desse pregão não traz o strike delas. `
      : "";
  $("gx-nota").innerHTML =
    conversao +
    buraco +
    `O GEX supõe formadores de mercado vendidos em calls e comprados em puts. No Brasil isso é menos confiável, ` +
    `então use como <b>zonas de interesse</b>, não como suporte ou resistência garantidos.` +
    sobreVol;

  /* grafico por strike, nos dois modos */
  function desenhar(modo) {
    const dados = [...linhas]
      .reverse()
      .map((l) => ({ K: l.strike, c: l.call_oi, p: l.put_oi, g: gexEm(S, l.strike, l.call_oi, l.put_oi) }));
    const max =
      modo === "oi"
        ? Math.max(...dados.map((x) => Math.max(x.c, x.p)))
        : Math.max(...dados.map((x) => Math.abs(x.g)));

    let html = "";
    let marcouPreco = false;
    dados.forEach((x) => {
      if (!marcouPreco && x.K < S) {
        html += `<div class="gx-price"><span>preço ${fmt(S, 2)}</span></div>`;
        marcouPreco = true;
      }
      const esq = modo === "oi" ? x.p : Math.max(0, -x.g);
      const dir = modo === "oi" ? x.c : Math.max(0, x.g);
      const marca = x.K === cw ? " cw" : x.K === pw ? " pw" : "";
      const dica =
        modo === "oi"
          ? `${x.K}: ${fmt(x.p)} puts, ${fmt(x.c)} calls`
          : `${x.K}: GEX ${x.g >= 0 ? "+" : "−"}R$ ${fmt(Math.abs(x.g) / 1e3)} mil`;
      html += `<div class="gx-row" title="${dica}"><div class="gx-l"><i style="width:${((esq / max) * 100).toFixed(1)}%"></i></div><span class="gx-k${marca}">${x.K}</span><div class="gx-r"><i style="width:${((dir / max) * 100).toFixed(1)}%"></i></div></div>`;
    });

    const ch = $("gxchart");
    ch.innerHTML = html;
    const primeiro = linhas[0].strike, ultimo = linhas[linhas.length - 1].strike;
    ch.setAttribute(
      "aria-label",
      modo === "oi"
        ? `Contratos em aberto por strike de ${primeiro} a ${ultimo}. Maior concentração de puts em ${pw} e de calls em ${cw}.`
        : `GEX por strike de ${primeiro} a ${ultimo}. Total ${total >= 0 ? "positivo" : "negativo"}.`
    );
    $("gxtitle").textContent = modo === "oi" ? "Contratos em aberto por strike" : "GEX por strike (R$ por 1%)";
    $("gxl").textContent = modo === "oi" ? "◄ Puts" : "◄ Gamma negativo";
    $("gxr").textContent = modo === "oi" ? "Calls ►" : "Gamma positivo ►";
    document.querySelectorAll(".gxb").forEach((b) => {
      const on = b.dataset.m === modo;
      b.classList.toggle("on", on);
      b.setAttribute("aria-pressed", on);
    });
  }

  document.querySelectorAll(".gxb").forEach((b) => b.addEventListener("click", () => desenhar(b.dataset.m)));
  desenhar("oi");
}

montar();
