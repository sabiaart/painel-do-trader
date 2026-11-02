"""Gera as paginas de texto do site (/sobre, /privacidade, /termos).

Elas compartilham o mesmo cabecalho e rodape. Em vez de repetir isso a mao em
tres arquivos (e esquecer de atualizar um deles depois), o molde fica aqui.

Rodar depois de qualquer mudanca no texto:

    python pipeline/gerar_paginas_texto.py
"""

from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SITE = RAIZ / "site"

MOLDE = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{titulo} | Painel do Trader</title>
<meta name="description" content="{descricao}">
<meta name="robots" content="noindex">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Condensed:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<link rel="stylesheet" href="/css/painel.css">
</head>
<body>

<a class="pular" href="#conteudo">Pular para o conteúdo</a>

<header>
  <div class="bar">
    <div class="brand">
      <div class="logo"><svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" style="color:var(--bg)" aria-hidden="true"><polyline points="3 17 9 11 13 15 21 7"/><polyline points="15 7 21 7 21 13"/></svg></div>
      <b>Painel do Trader</b>
    </div>
    <nav aria-label="Páginas">
      <a href="/">Painel</a><a href="/opcoes/">Opções</a><a href="/sobre/"{a_sobre}>Sobre</a><a href="/privacidade/"{a_priv}>Privacidade</a><a href="/termos/"{a_termos}>Termos</a>
    </nav>
  </div>
</header>

<div class="wrap">
  <main id="conteudo" class="panel texto">
    <h1 style="font-family:var(--display);font-size:28px;margin:0 0 6px">{titulo}</h1>
    <p class="muted" style="margin:0">Última atualização: {atualizado}.</p>
{corpo}
  </main>

  <footer>
    <div class="rodape-links">
      <a href="/">Painel</a>
      <a href="/opcoes/">Opções</a>
      <a href="/sobre/">Sobre e metodologia</a>
      <a href="/privacidade/">Privacidade</a>
      <a href="/termos/">Termos de uso</a>
      <a href="https://github.com/sabiaart/painel-do-trader">Código aberto</a>
    </div>
    Conteúdo informativo, não é recomendação de investimento.
  </footer>
</div>
</body>
</html>
"""

ATUALIZADO = "2 de novembro de 2026"

SOBRE = """
    <section>
      <h2>O que é o Painel do Trader</h2>
      <p>Um site gratuito que reúne, numa tela só, o contexto do mercado brasileiro
      para quem opera mini índice (WIN) e mini dólar (WDO): pré-mercado, fluxo,
      posicionamento, volatilidade, sentimento, agenda e opções.</p>
      <p><b>O que ele não é:</b> um terminal de cotações. Não mostramos preço em tempo
      real, não sugerimos operação e não dizemos para onde o mercado vai. O que o
      painel faz é organizar e interpretar dados públicos que os sites gratuitos
      não costumam juntar num lugar só.</p>
    </section>

    <section>
      <h2>Os quatro princípios</h2>
      <ol>
        <li><b>Informativo, nunca recomendação.</b> Nenhum texto desta página diz
        &ldquo;compre&rdquo; ou &ldquo;venda&rdquo;. Tudo é estatística e contexto.</li>
        <li><b>Dado de exemplo é sempre identificado.</b> Enquanto um bloco não tiver
        dado real, a tela avisa com todas as letras.</li>
        <li><b>Toda fonte é rastreável.</b> Cada número tem origem, horário de
        atualização e método descritos aqui nesta página.</li>
        <li><b>Celular primeiro.</b> O painel é feito para ser lido no telefone e no
        segundo monitor durante o pregão.</li>
      </ol>
    </section>

    <section>
      <h2>Metodologia</h2>

      <h3>Placar dos indicadores</h3>
      <p>Dez indicadores de pré-mercado, cada um valendo um ponto quando está
      favorável à alta do índice: S&amp;P 500 futuro, Nasdaq futuro, EWZ, ADRs de
      Vale, Petrobras e Itaú, minério em Dalian, Brent, DXY e Treasury de 10 anos.
      Nos dois últimos, a <i>queda</i> é o que conta como favorável.</p>
      <p>O placar descreve como o mundo amanheceu. Não é previsão: dias com placar
      alto fecham em queda com frequência.</p>

      <h3>Termômetro do mercado</h3>
      <p>Medidor de 0 a 100, de medo extremo a ganância extrema, com sete
      componentes: momento do Ibovespa, amplitude das ações, volatilidade,
      fluxo estrangeiro, posição do estrangeiro no WIN, proteção via opções e
      porto seguro (dólar).</p>
      <p>Cada componente vira um percentil dos últimos 252 pregões, invertendo os
      que indicam medo quando sobem. A nota final é a média simples dos sete.
      Zonas: 0–24 medo extremo, 25–44 medo, 45–55 neutro, 56–75 ganância,
      76–100 ganância extrema.</p>

      <h3>Movimento esperado</h3>
      <p>A faixa do dia sai de uma conta só:</p>
      <p class="num" style="font-size:16px">movimento de 1 desvio = preço × volatilidade anual × √(1/252)</p>
      <p>Um desvio cobre cerca de 68% dos dias; dois desvios, cerca de 95%. A faixa
      é centrada no ajuste anterior. Em dias de evento forte (Payroll, Copom, CPI,
      IPCA) a faixa é ampliada por um fator histórico, e a tela avisa quando isso
      acontece.</p>
      <p>A volatilidade vem do índice de volatilidade do Ibovespa para o WIN e das
      opções de dólar para o WDO. Quando nenhum dos dois está disponível, usamos
      volatilidade histórica, e o painel informa qual método foi usado.</p>
      <p>Acompanhamos o acerto: o painel mostra em quantos dos últimos 30 pregões a
      faixa foi respeitada.</p>

      <h3>Opções de BOVA11</h3>
      <p>O gamma de cada série vem de Black-Scholes. O GEX de cada strike é
      <span class="num">(OI_call − OI_put) × gamma × S² × 0,01</span>, em reais por
      1% de variação. Call wall e put wall são os strikes com maior
      <span class="num">OI × gamma</span>. O gamma flip é o preço mais próximo do
      atual em que o GEX total troca de sinal.</p>
      <p>Esse cálculo supõe formadores de mercado vendidos em calls e comprados em
      puts. No Brasil essa suposição é menos confiável do que nos Estados Unidos.
      Por isso tratamos os níveis como zonas de interesse, não como suporte ou
      resistência.</p>

      <h3>Tom das notícias</h3>
      <p>Manchetes de veículos de economia são classificadas por inteligência
      artificial pelo impacto provável na bolsa brasileira. A classificação é
      automática e erra. Esse módulo é marcado como leitura por IA e
      <b>não entra</b> no cálculo do termômetro.</p>
    </section>

    <section>
      <h2>Fontes</h2>
      <table>
        <tr><td><b>B3</b></td><td>Arquivos públicos de fim de dia: posições em aberto por participante, participação de investidores e prêmios de opções. Nunca raspamos o site da B3.</td></tr>
        <tr><td><b>Banco Central</b></td><td>Séries do sistema SGS.</td></tr>
        <tr><td><b>FRED</b></td><td>Séries públicas, entre elas o índice de volatilidade do EWZ.</td></tr>
        <tr><td><b>API de mercados globais</b></td><td>Futuros, ADRs, commodities e moedas, por serviço licenciado para exibição pública.</td></tr>
        <tr><td><b>Claude (IA)</b></td><td>Resumo do dia, resumo do fechamento e classificação das manchetes.</td></tr>
      </table>
      <p>Não exibimos cotações intradiárias de WIN e WDO: isso exige contrato de
      market data com a B3. Por isso a calculadora pede que <i>você</i> digite o
      preço que vê na sua plataforma.</p>
    </section>

    <section>
      <h2>Quando um dado falha</h2>
      <p>Se uma fonte sai do ar, o painel mantém o último dado válido e mostra a
      data dele. A página não quebra e nenhum bloco inventa número.</p>
    </section>

    <section>
      <h2>Em que fase o projeto está</h2>
      <p>O site está em construção. Hoje, <b>o único dado real é a
      volatilidade</b> que define a largura do movimento esperado: ela vem do
      Banco Central (dólar) e do FRED (EWZ), e é atualizada por um robô todo
      dia útil de manhã. Cada painel diz na tela de onde veio a sua
      volatilidade e de que dia é.</p>
      <p>Todo o resto ainda é exemplo, incluindo o ajuste anterior, a máxima e
      a mínima, que dependem dos arquivos de fim de dia da B3.</p>
      <p>A ordem das próximas etapas é: mercados globais, dados da B3, textos
      por IA, página de opções com dados reais e, por fim, enquete e alertas.</p>
      <p>O código é aberto e pode ser conferido no
      <a href="https://github.com/sabiaart/painel-do-trader">GitHub</a>.</p>
    </section>
"""

PRIVACIDADE = """
    <section>
      <p class="sample">Rascunho. Este texto ainda será revisado antes do
      lançamento e antes de qualquer pedido de aprovação no Google AdSense.</p>

      <h2>Resumo em uma frase</h2>
      <p>O Painel do Trader não pede cadastro, não pede seus dados e não sabe quem
      você é. O que existe de coleta vem de anúncios e de medição de audiência.</p>
    </section>

    <section>
      <h2>O que não coletamos</h2>
      <ul>
        <li>Não há cadastro, login ou senha.</li>
        <li>Não pedimos nome, e-mail, CPF nem dados da sua corretora.</li>
        <li>Não temos acesso à sua conta, à sua plataforma ou às suas operações.</li>
        <li>O preço que você digita na calculadora é calculado no seu próprio
        aparelho e não é enviado para lugar nenhum.</li>
      </ul>
    </section>

    <section>
      <h2>O que fica guardado no seu aparelho</h2>
      <p>A enquete do dia guarda o seu voto no armazenamento local do navegador,
      só para não perguntar duas vezes no mesmo dia. Esse registro não sai do seu
      aparelho e some quando você limpa os dados do navegador.</p>
    </section>

    <section>
      <h2>Anúncios</h2>
      <p>O site é gratuito e se mantém com publicidade. Os anúncios são fornecidos
      por redes de terceiros, que podem usar cookies para medir audiência e, se
      você consentir, exibir anúncios personalizados.</p>
      <p>Você pode recusar os anúncios personalizados no aviso de cookies. Recusar
      não tira nenhuma funcionalidade do painel.</p>
    </section>

    <section>
      <h2>Seus direitos (LGPD)</h2>
      <p>A Lei Geral de Proteção de Dados garante a você o direito de saber quais
      dados existem a seu respeito, corrigi-los, apagá-los e retirar o
      consentimento a qualquer momento.</p>
      <p>Como não mantemos cadastro, na prática não há dado pessoal nosso para
      apagar. Para pedidos relativos aos cookies de publicidade, fale com a rede
      de anúncios correspondente ou use o aviso de cookies deste site.</p>
    </section>

    <section>
      <h2>Contato</h2>
      <p>O canal de contato será publicado junto com o lançamento no domínio
      definitivo.</p>
    </section>
"""

TERMOS = """
    <section>
      <p class="sample">Rascunho. Este texto ainda será revisado antes do
      lançamento no domínio definitivo.</p>

      <h2>1. Isto não é recomendação de investimento</h2>
      <p>O Painel do Trader é um site de <b>conteúdo informativo e estatístico</b>.
      Nada aqui é recomendação, sugestão, indicação ou aconselhamento de
      investimento, nem oferta de compra ou venda de qualquer ativo.</p>
      <p>Não somos analistas de valores mobiliários, consultores nem
      administradores de carteira, e não prestamos nenhum desses serviços.</p>
      <p>As decisões que você toma no mercado são suas, e o risco é seu.</p>
    </section>

    <section>
      <h2>2. O que os números significam</h2>
      <p>Faixas, percentuais, placares e termômetros deste site descrevem o que
      <i>já aconteceu</i> e com que frequência certas coisas ocorreram no passado.
      Não preveem o futuro.</p>
      <p>Uma faixa de 1 desvio cobre cerca de 68% dos dias. Isso quer dizer que,
      historicamente, cerca de um dia em cada três ficou fora dela.</p>
    </section>

    <section>
      <h2>3. Sem garantia sobre os dados</h2>
      <p>Trabalhamos com dados públicos de terceiros e com cálculos próprios.
      Pode haver atraso, erro, falha de fonte ou interrupção. Os dados são
      oferecidos no estado em que estão, sem garantia de exatidão,
      disponibilidade ou adequação a qualquer finalidade.</p>
      <p>Não exibimos cotações intradiárias de WIN e WDO. Os valores mostrados são
      de fim de dia, e o preço usado na calculadora é aquele que você mesmo
      digita.</p>
    </section>

    <section>
      <h2>4. Limitação de responsabilidade</h2>
      <p>Não respondemos por perdas, prejuízos, lucros cessantes ou qualquer dano
      decorrente do uso ou da impossibilidade de uso deste site, nem por decisões
      tomadas com base nele.</p>
    </section>

    <section>
      <h2>5. Uso do site</h2>
      <p>O uso é gratuito e pessoal. Você não pode usar o site de forma que
      prejudique o funcionamento dele ou de terceiros, nem redistribuir os dados
      de forma automatizada em escala.</p>
      <p>O código do site é aberto e está no
      <a href="https://github.com/sabiaart/painel-do-trader">GitHub</a>, com a
      licença indicada no repositório. Os dados de terceiros seguem as licenças
      das respectivas fontes.</p>
    </section>

    <section>
      <h2>6. Enquete</h2>
      <p>A enquete de humor é anônima, sem prêmio de qualquer espécie e sem
      ranking. Ela retrata como os visitantes dizem estar posicionados, não o que
      eles deveriam fazer.</p>
    </section>

    <section>
      <h2>7. Mudanças</h2>
      <p>Estes termos podem mudar conforme o site evolui. A data no topo indica a
      última versão.</p>
    </section>
"""

PAGINAS = [
    ("sobre", "Sobre e metodologia",
     "O que é o Painel do Trader, como cada indicador é calculado e de onde vem cada dado.",
     SOBRE),
    ("privacidade", "Política de privacidade",
     "O que o Painel do Trader coleta, o que não coleta e quais são os seus direitos pela LGPD.",
     PRIVACIDADE),
    ("termos", "Termos de uso",
     "Condições de uso do Painel do Trader e aviso de que o conteúdo não é recomendação de investimento.",
     TERMOS),
]


def main() -> None:
    atual = ' aria-current="page"'
    for pasta, titulo, descricao, corpo in PAGINAS:
        destino = SITE / pasta
        destino.mkdir(parents=True, exist_ok=True)
        html = MOLDE.format(
            titulo=titulo,
            descricao=descricao,
            atualizado=ATUALIZADO,
            corpo=corpo.rstrip(),
            a_sobre=atual if pasta == "sobre" else "",
            a_priv=atual if pasta == "privacidade" else "",
            a_termos=atual if pasta == "termos" else "",
        )
        (destino / "index.html").write_text(html, encoding="utf-8", newline="\n")
        print(f"gerado: site/{pasta}/index.html")


if __name__ == "__main__":
    main()
