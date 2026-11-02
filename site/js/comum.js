/* Funcoes usadas por mais de uma pagina do Painel do Trader. */

/* Formata numero no padrao brasileiro: 1.234,5 */
export const fmt = (v, casas = 0) =>
  Number(v).toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });

/* Le um preco digitado pelo usuario nos formatos brasileiros:
   129.200 / 129200 / 5.436,0 / 5436,5 */
export function parsePreco(s) {
  s = String(s).trim().replace(/\s/g, "");
  if (!s) return NaN;
  if (s.includes(",")) s = s.replace(/\./g, "").replace(",", ".");
  else if (/^\d{1,3}(\.\d{3})+$/.test(s)) s = s.replace(/\./g, "");
  return parseFloat(s);
}

/* Busca um JSON de site/data/. Nunca deixa a pagina quebrar:
   em caso de falha devolve null e quem chamou mostra um aviso. */
export async function carregar(nome) {
  try {
    const r = await fetch(`/data/${nome}.json`, { cache: "no-cache" });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return await r.json();
  } catch (e) {
    console.warn(`Nao foi possivel carregar ${nome}.json:`, e.message);
    return null;
  }
}

/* Escreve o aviso de dado de exemplo e a data do dado.
   Enquanto "exemplo" for true, a tela precisa deixar isso claro. */
export function marcarOrigem(dados, elId = "aviso-exemplo") {
  const el = document.getElementById(elId);
  if (!el || !dados) return;
  const quando = dados.gerado_em
    ? new Date(dados.gerado_em).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })
    : null;
  /* Fonte fora do ar: o pipeline manteve o dado anterior e marcou isso.
     A tela precisa dizer de quando é o número, nunca fingir que é de hoje. */
  if (dados.desatualizado) {
    el.innerHTML = `A fonte não respondeu na última atualização. ` +
      `Mostrando o <b>último dado válido</b>${quando ? `, de ${quando}` : ""}.`;
  } else if (dados.exemplo) {
    el.innerHTML = `Esta página mostra <b>dados de exemplo</b>. Nenhum número é real.` +
      (quando ? ` <span class="muted">Arquivo de ${quando}.</span>` : "");
  } else if (quando) {
    el.innerHTML = `Dados de <b>${quando}</b>. Fonte: ${dados.origem || "não informada"}.`;
  }
  el.hidden = false;
}

/* Marca UM bloco como dado de exemplo.
   A pagina hoje e mista: uns blocos ja tem dado real, outros nao. Um aviso
   so no topo mentiria para os dois lados, entao cada bloco diz o que e. */
export function marcarBloco(dados, id) {
  const bloco = document.getElementById(id);
  if (!bloco || !dados) return false;
  if (!dados.exemplo && !dados.desatualizado) return false;

  const selo = document.createElement("span");
  selo.className = "tag-exemplo";
  selo.textContent = dados.desatualizado ? "dado antigo" : "exemplo";
  selo.title = dados.desatualizado
    ? "A fonte não respondeu. Este bloco mostra o último dado válido."
    : "Este bloco ainda não tem dado real.";

  /* Entra ao lado do titulo quando existe um; senao, no topo do bloco. */
  const cabecalho = bloco.querySelector(".head") || bloco.querySelector(".label")?.parentElement;
  if (cabecalho) cabecalho.appendChild(selo);
  else bloco.prepend(selo);
  return true;
}

/* Mostra uma mensagem curta no rodape da tela. */
export function aviso(msg) {
  const t = document.getElementById("toast");
  if (!t) return;
  t.textContent = msg;
  t.hidden = false;
  clearTimeout(aviso._t);
  aviso._t = setTimeout(() => (t.hidden = true), 2400);
}

/* Troca o conteudo de um bloco por um aviso quando o dado nao veio. */
export function semDado(el, nome) {
  if (el) el.innerHTML = `<p class="erro">Não foi possível carregar ${nome} agora. O restante da página continua funcionando.</p>`;
}
