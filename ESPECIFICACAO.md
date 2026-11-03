# Painel do Trader — Especificação do projeto

Documento de partida para o desenvolvimento. Reúne as decisões tomadas na fase de planejamento. O protótipo visual está em `prototipo/painel-trader.html`.

---

## 1. Visão geral

**O que é:** um site gratuito que reúne, numa tela só, o **contexto do mercado brasileiro** para quem opera mini índice (WIN) e mini dólar (WDO): pré-mercado, fluxo, posicionamento, volatilidade, sentimento, agenda e opções.

**O que não é:** um terminal de cotações. O diferencial é organizar e interpretar dados que os sites gratuitos (Investing, TradingView) não juntam.

**Público:** day traders e swing traders brasileiros de WIN e WDO. Acesso majoritário pelo celular, e pelo segundo monitor durante o pregão.

**Metas iniciais**
- Popularidade primeiro: chegar a cerca de 5 mil acessos por dia.
- Receita: até R$ 3 mil por mês com anúncios e afiliados já é um bom resultado.
- Custo de operação próximo de zero no primeiro ano.

**Princípios**
1. **Informativo, nunca recomendação.** Nada de "compre", "venda" ou "o índice vai subir". Tudo é estatística e contexto (regras da CVM).
2. **Dados de exemplo sempre identificados.** Enquanto um bloco não tiver dado real, a tela mostra isso claramente.
3. **Fonte de cada número rastreável.** Cada dado tem origem, horário de atualização e método conhecido.
4. **Celular primeiro.** Tudo precisa funcionar bem a 400px de largura.

---

## 2. Restrições legais e de dados (ler antes de codar)

- **Proibido raspar o site da B3.** A B3 proíbe expressamente a coleta automatizada nas páginas de cotações, inclusive por ferramentas de IA. Use apenas **arquivos públicos de download** cujos termos permitam o uso, ou **APIs de terceiros licenciadas**. Verificar os termos de cada arquivo antes de automatizar (ver seção 10).
- **Cotações da B3 exigem contrato**, mesmo com 15 minutos de atraso. A nova Política de Market Data (em vigor desde 01/11/2026) permite distribuição em atraso contínuo em sites abertos, mas ainda via contrato. **No MVP não exibimos cotações intradiárias de WIN/WDO.** Usamos dados de fim de dia e o preço digitado pelo próprio usuário.
- **APIs de mercados globais:** confirmar que o plano permite **exibição pública** (muitos planos gratuitos só permitem uso pessoal).
- **CVM:** textos da IA e alertas descrevem, não recomendam. Rodapé fixo: "Conteúdo informativo, não é recomendação de investimento."
- **AdSense:** nunca clicar nos próprios anúncios. Exige páginas de Política de Privacidade e Termos, além do `ads.txt`.
- **LGPD:** aviso de cookies e consentimento para anúncios personalizados.
- **Palpites e enquetes:** sem prêmio em dinheiro ou bens (exigiria autorização do governo).

---

## 3. Arquitetura

Site **estático** que lê arquivos JSON gerados por um **robô agendado**. Simples, rápido e gratuito.

```
GitHub (repositório)
 ├── site/            → páginas estáticas (HTML/CSS/JS ou gerador estático leve, ex.: Astro)
 ├── pipeline/        → scripts Python que baixam dados e calculam indicadores
 ├── data/            → JSONs gerados pelo pipeline (o site só lê daqui)
 └── .github/workflows → agendamentos
```

- **Hospedagem:** Cloudflare Pages (gratuito). Alternativas: Vercel, Netlify.
- **Robô:** GitHub Actions com agendamento.
  - Pré-mercado: por volta de 07h00 (Brasília) = 10h00 UTC. Agendar uns 20 minutos antes, porque o cron do GitHub pode atrasar.
  - Fechamento: por volta de 18h30 (Brasília) para o resumo do dia e o resultado das faixas.
- **Funções dinâmicas** (enquete, bot do Telegram): Cloudflare Workers + KV ou D1 (planos gratuitos).
- **IA:** API do Claude. Modelo padrão: Claude Haiku 5.5 (barato). Sonnet 5.5 se a qualidade do texto não bastar.
- **Fluxo de cada execução:** baixar → validar → calcular → gravar JSON em `data/` → commit → deploy automático.
- **Se uma fonte falhar:** manter o último dado válido, marcar o horário dele e exibir "dado de [data]" na tela. Nunca quebrar a página.

**Páginas**
| Endereço | Conteúdo |
|---|---|
| `/` | Painel principal |
| `/opcoes` | Opções de BOVA11: contratos em aberto e GEX (página separada para gerar nova visualização e novos anúncios) |
| `/sobre` | O que é o painel, metodologia e fontes |
| `/privacidade` | Política de privacidade (obrigatória para AdSense) |
| `/termos` | Termos de uso e aviso de não recomendação |

---

## 4. Módulos do painel

Cada módulo lê um JSON próprio em `data/`. Abaixo: o que mostra, a fonte e o cálculo.

### 4.1 Placar dos indicadores (topo)
- **Mostra:** "7 de 10 indicadores do pré-mercado apontam para alta", com uma barra de 10 segmentos. Nunca escrever "previsão".
- **Indicadores (cada um vale 1 ponto se favorável à alta):** S&P 500 futuro, Nasdaq futuro, EWZ, ADR da Vale, ADR da Petrobras, ADR do Itaú, minério em Dalian, Brent, DXY (queda favorável), Treasury de 10 anos (queda favorável).
- **Fonte:** API de mercados globais (Twelve Data, Finnhub ou FMP, conforme licença).

### 4.2 Resumo do dia (IA)
- **Mostra:** 3 linhas: (1) como amanhecem Nova York e o EWZ; (2) commodities e dólar; (3) o evento da agenda que pode mudar o humor.
- **Como:** o pipeline monta um resumo dos dados do dia e envia ao Claude com instruções fixas: português simples, sem recomendação, sem previsão de preço, máximo de 3 frases curtas.
- **Fechamento:** um segundo resumo às 18h30 com o que aconteceu e se as faixas foram respeitadas.

### 4.3 O que mexe hoje
- **Mostra:** grade com os 10 ativos do placar: valor, variação e "peso no WIN" (alto ou médio, definido manualmente num arquivo de configuração).

### 4.4 Termômetro do mercado (medo e ganância)
- **Mostra:** medidor de 0 a 100 (medo extremo a ganância extrema), valores de ontem, de uma semana e de um mês atrás, e a lista dos 7 componentes com suas notas.
- **Componentes:**
  1. Momento: Ibovespa contra a média de 125 dias.
  2. Amplitude: % das ações do Ibovespa acima da média de 200 dias.
  3. Volatilidade: S&P/B3 Ibovespa VIX contra a média de 50 dias (volatilidade alta = medo).
  4. Fluxo estrangeiro: saldo dos últimos 5 pregões.
  5. Posição do estrangeiro no WIN: posição líquida.
  6. Proteção: put/call ratio das opções de BOVA11 (mais puts = medo).
  7. Porto seguro: dólar contra a média (dólar subindo = medo).
- **Cálculo:** cada componente vira um **percentil dos últimos 252 pregões** (0 a 100, invertendo os que indicam medo quando sobem). A nota final é a média simples.
- **Zonas:** 0–24 medo extremo, 25–44 medo, 45–55 neutro, 56–75 ganância, 76–100 ganância extrema.

### 4.5 Tom das notícias (IA) — separado do termômetro
- **Mostra:** saldo do dia ("levemente positivo"), contagem de manchetes positivas, neutras e negativas, e as principais manchetes com a classificação. Selo "Leitura por IA" e aviso de que a classificação é automática.
- **Como:** coletar manchetes por RSS de veículos de economia (respeitar os termos de cada um e usar só título e link). O Claude classifica cada manchete pelo impacto provável na bolsa brasileira.
- **Importante:** este módulo **não entra** no cálculo do termômetro.

### 4.6 Humor da comunidade (enquete)
- **Mostra:** "Como você entra hoje no WIN?", com as opções Comprado, Vendido e De fora, e as barras de resultado.
- **Regras:** 1 voto por dispositivo por dia. Sem ranking público e sem certo ou errado. No fechamento, mostrar o contraste: "ontem 58% estavam comprados e o WIN fechou em queda de 0,4%".
- **Backend:** Cloudflare Worker + KV. Armazenar apenas contagens, sem dados pessoais.

### 4.7 Fluxo estrangeiro
- **Mostra:** barras dos últimos 20 pregões (R$ bi) e o saldo de ontem, do mês e do ano.
- **Fonte:** estatísticas públicas da B3 sobre participação de investidores, ou a API do Dados de Mercado (histórico desde 2010). Verificar os termos.

### 4.8 Quem está comprado no WIN
- **Mostra:** saldo de contratos por participante (estrangeiro, institucional, pessoa física, instituição financeira), a variação em 5 dias e uma leitura automática em uma frase.
- **Fonte:** posições em aberto de derivativos por tipo de participante, publicadas pela B3 (fim de dia). Verificar os termos.

### 4.9 Níveis do dia e movimento esperado (WIN e WDO)
- **Mostra:** ajuste anterior, gap previsto, máxima e mínima de ontem, dias para o vencimento e a barra do movimento esperado (faixas de 1 e 2 desvios centradas no ajuste).
- **Fórmula:** `movimento_1_desvio = preço × vol_anual × √(1/252)`
  - Exemplo: WIN 128.450, vol 17% → cerca de ±1.375 pontos.
  - 1 desvio ≈ 68% dos dias; 2 desvios ≈ 95%.
- **Fontes de volatilidade:**
  - **Índice:** S&P/B3 Ibovespa VIX (fechamento anterior). Reserva: VXEWZ (Cboe, série pública no FRED).
  - **Dólar:** não há índice pronto. Calcular a volatilidade implícita das opções de dólar mais negociadas perto do dinheiro com o modelo **Black-76**, usando os prêmios de fechamento.
  - **Plano B dos dois:** volatilidade histórica (ATR de 14 dias ou GARCH). O painel indica qual método foi usado.
- **Dia de evento:** em dias de Payroll, Copom, CPI ou IPCA, ampliar a faixa pelo fator histórico do evento (configurável; exemplo +30%) e avisar na tela.
- **Placar de acerto:** "faixa respeitada em X dos últimos 30 pregões", calculado com máxima e mínima de fim de dia.

### 4.10 Calculadora "Onde o preço está na faixa"
- **Mostra:** o usuário escolhe WIN ou WDO e **digita o preço que vê na plataforma dele** (evita licença de dados em tempo real).
- **Calcula:**
  - `% percorrido = |preço − ajuste| / movimento_1_desvio`
  - Zona: dentro de 1 desvio, entre 1 e 2, ou além de 2 ("esticado").
  - Pontos que faltam para a próxima faixa.
- **Aceita** os formatos brasileiros: `129.200`, `129200`, `5.436,0`, `5436,5`.
- **Fechamento:** "ontem o WIN percorreu 118% do movimento esperado".
- O protótipo já tem essa lógica funcionando em JavaScript.

### 4.11 Agenda que move o mercado
- **Mostra:** horário, evento, impacto (alto ou médio), o movimento histórico médio do WIN nesses dias e o contador de dias para o vencimento do WIN e do WDO.
- **Fonte no MVP:** curadoria manual num arquivo `data/agenda.json`, com 3 a 5 eventos por semana. Depois, avaliar uma API de calendário econômico.
- **Histórico:** calcular a variação média do WIN nos dias de cada tipo de evento a partir do histórico de fim de dia.

### 4.12 Página `/opcoes` — BOVA11
- **Mostra:**
  - Quatro números: **call wall**, **put wall**, **gamma flip** e **GEX total**, convertidos para pontos do Ibovespa pela relação do dia entre o índice e o BOVA11.
  - Gráfico por strike com dois modos: **contratos em aberto** (puts à esquerda, calls à direita) e **GEX** (gamma negativo à esquerda, positivo à direita), com a linha do preço atual.
  - Anúncio dentro do conteúdo e seção "Como ler esta página".
- **Dados:** contratos em aberto por série do vencimento mensal e prêmios de fechamento (fonte a confirmar; ver seção 10).
- **Cálculo** (o protótipo já implementa):
  - Gamma por Black-Scholes, com a volatilidade implícita de cada série (ou a do VIX do Ibovespa, como aproximação).
  - `GEX(strike) = (OI_call − OI_put) × gamma × S² × 0,01` (R$ por 1% de variação). **Confirmar a unidade do open interest no arquivo da B3** (opções ou lotes) e aplicar o multiplicador correto.
  - Call wall e put wall: strikes com maior `OI × gamma` de calls e de puts.
  - Gamma flip: varrer preços hipotéticos e achar onde o GEX total troca de sinal, o mais próximo do preço atual.
- **Aviso fixo:** o GEX supõe formadores de mercado vendidos em calls e comprados em puts. No Brasil isso é menos confiável, então os níveis são "zonas de interesse".

### 4.13 Alertas no Telegram
- **Canal gratuito**, com no máximo 4 alertas por dia: abertura, eventos da agenda, rompimento de faixa (calculado no fechamento até haver dado intradiário licenciado) e fechamento.
- **Regra:** **o alerta avisa, o site explica.** O alerta nunca entrega a informação completa. Exemplo: "WIN rompeu a faixa de 1 desvio. Veja o que aconteceu nos dias parecidos" + link.
- **Links com UTM**, para medir os cliques de cada tipo de alerta.

### 4.14 Card do dia (compartilhável)
- **Imagem gerada automaticamente** às 7h com placar, termômetro, movimento esperado e evento principal, no formato 1080×1350 (Instagram) e 1080×1920 (stories e status).
- Botão "Gerar card do dia" no painel. A mesma imagem alimenta o Instagram e o Telegram.
- **Como gerar:** renderizar um HTML do card com Playwright (ou Satori) no próprio pipeline.

---

## 5. Anúncios e monetização

- **Rede:** Google AdSense no início. Depois, venda direta do topo e do card "Parceiro" para corretoras, com preço mensal fixo.
- **Espaços:**
  - Topo: 728×90 ou 970×90 no desktop, 320×100 no celular.
  - Lateral: 300×600 + 300×250 (só desktop).
  - **No celular:** um anúncio **entre blocos** (depois de "O que mexe hoje"), porque a coluna lateral vai para o fim da página e quase ninguém chega lá.
  - `/opcoes`: anúncio dentro do conteúdo + lateral.
- **Afiliados:** card "Parceiro" com link de abertura de conta em corretora (rastreado).
- **Arquivos obrigatórios:** `ads.txt`, política de privacidade, termos e banner de cookies.
- **Estimativa de referência:** com 150 mil visitas por mês em finanças, R$ 1.500 a R$ 3.500 por mês só com AdSense.

---

## 6. SEO e divulgação

- Título e descrição únicos por página. Texto explicativo em cada ferramenta (metodologia, perguntas frequentes).
- `sitemap.xml`, `robots.txt`, Open Graph (a imagem de prévia pode ser o card do dia).
- Página leve e rápida no celular.
- **Instalável na tela inicial** (PWA simples: manifest + ícone).
- Divulgação: perfil no Instagram sem rosto com o card diário, canal no Telegram e grupos de WhatsApp.

---

## 7. Design

- Usar `prototipo/painel-trader.html` como referência visual e de conteúdo. O arquivo é um fragmento (sem `<head>` completo) feito para pré-visualização.
- **Tipografia:** IBM Plex Sans Condensed (títulos), IBM Plex Sans (texto), IBM Plex Mono (números, com `tabular-nums`).
- **Tema escuro como padrão**, com tema claro seguindo o aparelho. Cores definidas como variáveis CSS (ver `:root` do protótipo).
- **Cores com significado:** verde-azulado para alta, laranja para baixa. Não usar só a cor para transmitir informação; acompanhar com seta ou texto.
- **Acessibilidade:** botões reais, áreas de toque de 44px ou mais, contraste mínimo de 4,5:1 e gráficos com descrição (`aria-label`).

---

## 8. Fases de desenvolvimento

| Fase | Entrega | Pronto quando |
|---|---|---|
| **0. Base** | Repositório, estrutura de pastas, deploy no Cloudflare Pages, domínio provisório | Site de teste no ar |
| **1. Site com dados de exemplo** | Todas as páginas do protótipo como site real, lendo JSONs de exemplo em `data/`, com `/opcoes` como página própria | Navegação completa no celular e no desktop |
| **2. Dados gratuitos e seguros** | Pipeline com fontes sem dúvida de licença: Banco Central (SGS), FRED (VXEWZ), API global com licença de exibição. Movimento esperado com volatilidade histórica | Painel atualiza sozinho às 7h |
| **3. Dados da B3** | Depois de confirmar os termos: fluxo estrangeiro, posições por participante, VIX do Ibovespa, opções de dólar (Black-76) | Termômetro e movimento esperado com dados reais |
| **4. IA** | Resumo do dia, resumo do fechamento e tom das notícias | Textos gerados todo dia sem intervenção |
| **5. Opções** | `/opcoes` com dados reais de BOVA11 | GEX calculado no robô das 7h |
| **6. Engajamento** | Enquete (Worker + KV), card do dia, canal e bot do Telegram | Card publicado e alertas enviados automaticamente |
| **7. Lançamento** | Domínio .com.br, páginas legais, `ads.txt`, AdSense, Search Console, analytics | Site aprovado no AdSense |
| **Depois** | Cotações com atraso licenciadas, faixa consumida automática, "dias parecidos com hoje", "pergunte ao painel", versão para o exterior | — |

---

## 9. Custos estimados (primeiro ano)

| Item | Custo |
|---|---|
| Domínio .com.br (Registro.br) | R$ 40/ano |
| Hospedagem (Cloudflare Pages) | R$ 0 |
| Robô (GitHub Actions, cota gratuita) | R$ 0 |
| Enquete e bot (Cloudflare Workers) | R$ 0 |
| API do Claude (Haiku 5.5) | menos de R$ 15/ano |
| **Total mínimo** | **cerca de R$ 55/ano** |

Custos possíveis depois: licença de cotações da B3 com atraso (via distribuidor), VPS (R$ 25 a R$ 50 por mês) se o robô precisar de mais, e plano pago de API de mercados globais.

---

## 10. Pendências a verificar antes de usar cada fonte

- [x] ~~Termos de uso dos **arquivos públicos de download da B3**~~ — **RESPONDIDO EM 02/11/2026: NÃO.** Ver abaixo.
- [ ] Se não forem: qual **API de terceiros** licenciada oferece esses dados, e a que preço?
- [ ] Termos de exibição do **S&P/B3 Ibovespa VIX** (site da S&P DJI).
- [ ] Licença de **exibição pública** da API de mercados globais escolhida.
- [ ] **Unidade do open interest** nas opções de BOVA11 (por opção ou por lote) e o multiplicador correto no GEX.
- [ ] Termos dos **feeds RSS** de notícias usados no tom das notícias.
- [ ] Custo de **cotações com atraso** da B3 via distribuidor (para a fase "Depois").

### Resposta sobre a B3, obtida em 02/11/2026

As páginas de dados da B3 trazem este aviso, palavra por palavra:

> "Os dados e informações disponibilizados nesta página são de propriedade
> exclusiva da B3 e destinam-se estritamente à consulta informativa, conforme
> Termos e Condições de Uso. Para manutenção da segurança do site e integridade
> dos dados e informações disponibilizados, **é expressamente vedada a coleta
> automatizada, inclusive por meio de ferramentas de inteligência artificial,
> para quaisquer finalidades, comerciais ou não, próprias ou de terceiros**."

Verificado em duas páginas diferentes, inclusive na de download dos arquivos
históricos. O aviso é geral, não é de uma página só.

Isso fecha a porta da Fase 3 como ela estava escrita:

- "coleta automatizada" cobre o robô baixando arquivo, não só raspagem de tela.
- "para quaisquer finalidades, comerciais ou não" — uso pessoal não ajuda.
- "inclusive por meio de ferramentas de inteligência artificial" — explícito.

Caminhos que sobram, a decidir:

- [ ] **API de terceiros licenciada** que redistribua dados da B3 (a própria
  especificação cita Dados de Mercado para o fluxo estrangeiro). Levantar quais
  existem, o que cobrem e a que preço.
- [ ] **Download manual pelo dono.** A proibição é da coleta *automatizada*.
  Uma pessoa baixando o arquivo e colocando numa pasta é consulta informativa,
  e o robô nunca toca no site da B3: ele só lê o arquivo que já está no
  computador. Serve para o painel pessoal offline. Para um site público
  continuaria faltando licença.
- [ ] Deixar os blocos que dependem da B3 fora do painel.

### Pesquisa de APIs brasileiras, 02/11/2026

Testadas: brapi.dev, Mais Retorno, HG Brasil, bolsai, BrasilAPI.

**O que existe de graca (brapi.dev), testado e funcionando:**

| Dado | Endpoint | Token? |
|---|---|---|
| WIN e WDO: ajuste, maxima, minima, vencimento, variacao | `/api/v2/futures/quote?symbols=WINZ26` | nao precisa |
| Serie diaria de ~1 ano do mesmo contrato | `/api/v2/futures/historical?symbol=WINZ26` | nao precisa |
| Ibovespa (^BVSP) | `/api/quote/%5EBVSP` | token gratuito |

A documentacao diz: "Sem token, aceita so symbols que comecam com WIN ou WDO".
Conferido: o ajuste do WDOX26 (5.421,2) bate exatamente com o PTAX do Banco
Central (5,4212 x 1000), o que da confianca na origem do numero.

Isso resolve de graca: ajuste/maxima/minima reais de WIN e WDO, volatilidade
historica do proprio WIN (hoje usa o VXEWZ como aproximacao) e o placar de
"faixa respeitada em X dos ultimos 30 pregoes".

**O que NAO existe em nenhuma API gratuita:**

- Fluxo estrangeiro (participacao dos investidores).
- Posicoes em aberto por tipo de participante (estrangeiro, institucional, PF).

Esses dois continuam dependendo de download manual ou de servico pago.

**Ressalva de licenca, a decidir:** a brapi declara no proprio site que "nao e
distribuidora nem redistribuidora licenciada da B3" e que reune "dados de
fontes abertas e publicas... apenas para fins informativos". A especificacao
pedia "APIs de terceiros licenciadas", entao, ao pe da letra, a brapi nao
atende esse criterio. Para o painel pessoal offline o risco e baixo. Para um
site publico, a pergunta continua aberta.

- [ ] Decidir se a brapi serve, apesar de ela nao se declarar licenciada.

### Acrescentado em 02/11/2026, depois da pesquisa de APIs

- [ ] **Nenhuma API de mercados globais pesquisada permite exibição pública em plano barato.** Twelve Data, Finnhub, FMP, EODHD e Polygon (hoje Massive) tratam os planos de autoatendimento como uso pessoal e não comercial; exibição pública exige plano empresarial ou contrato negociado. O gargalo não é o fornecedor: é a licença das bolsas (NYSE, Nasdaq, CME, ICE, DCE) por baixo. Decidir entre adiar o bloco de globais ou orçar centenas de dólares por mês.
- [ ] **VXEWZCLS (volatilidade do EWZ), já em uso no site.** O FRED marca a série como "Copyrighted: Citation required", da Cboe. A citação já foi colocada na tela, mas duas coisas seguem em aberto: se exibição em site com anúncios se enquadra no uso permitido, e se a proibição de "store, cache, or archive" do FRED alcança o nosso JSON. Resolver com o FRED (stlsFRED@stls.frb.org) ou com a Cboe **antes da Fase 7**, que é quando entram os anúncios.
- [ ] Séries do FRED vindas de órgãos do governo americano (DGS10, Treasury; DCOILBRENTEU, Brent/EIA) são "Public Domain: Citation requested" e não têm esse problema. Preferir essas sempre que der.

---

## 11. Como trabalhar com o dono do projeto

- O dono do projeto **não é programador**. Explique as decisões em português simples, com passos curtos.
- **Pergunte antes de** contratar qualquer serviço pago, criar contas em nome dele ou publicar algo no domínio definitivo.
- Faça commits pequenos e frequentes, com mensagens claras em português.
- Ao terminar cada fase, mostre o resultado no navegador e liste o que ficou pendente.

### Acrescentado em 02/11/2026: download manual da B3

Os dois blocos que nenhuma API gratuita cobre - fluxo estrangeiro (4.7) e
posicoes por participante (4.8) - passam a vir de arquivo baixado a mao.

- Pasta de entrada: `b3-manual/`, com instrucoes em `b3-manual/LEIA-ME.md`.
- Leitor: `pipeline/planilha.py` (CSV e XLSX, so biblioteca padrao) e
  `pipeline/manuais.py` (interpreta e acumula historico).
- **O robo nunca acessa b3.com.br.** Le so o que ja esta no computador.
- Pasta vazia nao e falha: o bloco mantem o ultimo dado valido com a data.

**Decisao tomada sem consultar: os dois JSON sairam do Git.** O repositorio e
publico e `site/data/fluxo.json` e `site/data/participantes.json` passariam a
conter dado derivado da B3. Consultar e uma coisa; republicar num repositorio
aberto e outra, com outra licenca. Eles agora sao gerados so no computador
local. Efeito colateral: no site hospedado esses dois blocos ficam sem dado
ate que se decida o contrario.

- [ ] Confirmar os caminhos de menu no site da B3 para os dois relatorios.
      Foram escritos de memoria, sem acessar o site.
- [ ] Decidir se os dois JSON voltam para o Git quando o site for publico.

### Acrescentado em 02/11/2026: a B3 juntou tudo no Boletim Diario

O usuario trouxe o aviso do site: desde 07/04/2025, contratos em aberto
passam a ser consultados no Boletim Diario do Mercado, capitulo Cotacoes -
Resumo Estatistico; e a participacao por tipo de investidor, no capitulo
Indicadores e Informativos, tabela Participacao dos Investidores.

Consequencias:

- **Bloco 4.7 (fluxo estrangeiro): viavel.** A tabela Participacao dos
  Investidores tem compras e vendas por tipo, em R$ mil, com colunas de
  porcentagem no meio. Nao tem coluna de saldo. O leitor foi ajustado para
  calcular compras menos vendas e ignorar as porcentagens - sem isso, ele
  pegaria a porcentagem achando que era dinheiro.
- **Bloco 4.8 (quem esta comprado no WIN): em risco.** O Resumo Estatistico
  traz contratos em aberto POR CONTRATO, nao por tipo de participante. Se a
  divisao por participante tiver mesmo saido do publico, o bloco como esta
  na secao 4.8 nao tem fonte gratuita.
- O Boletim guarda so os ultimos 10 dias. Historico mais longo exige baixar
  todo dia ou pagar.

- [ ] Confirmar, com um arquivo de verdade na mao, se o Resumo Estatistico
      ainda separa por tipo de participante.
- [ ] Se nao separar: decidir entre trocar o 4.8 por contratos em aberto
      totais do WIN (dado real, bloco mais fraco), remover o bloco, ou pagar.

### Acrescentado em 02/11/2026: coleta automatica da B3, e o que ela achou

**Decisao do dono, com o texto dos termos a vista.** Eu li a pagina do
Boletim Diario e ela proibe coleta automatizada em qualquer finalidade,
comercial ou nao, citando ferramentas de IA. Mostrei a frase. A decisao foi
seguir mesmo assim, como painel pessoal, sem republicacao. A regra antiga do
CLAUDE.md ("nunca raspar a B3") foi retirada a pedido dele.

A coleta esta em `pipeline/b3.py`, que abre com esse aviso escrito.

**A API do Boletim** (descoberta observando o proprio site):

    GET  /bdi/table/classifications              lista capitulos e tabelas
    GET  /bdi/table/workdays?date=AAAA-MM-DD     pregoes
    POST /bdi/table/{tabela}/{de}/{ate}/{pag}/{n}   dados

Tabelas que importam: `SharesInvesVolum` (participacao dos investidores) e
`AnalyticalFramework2` (quadro analitico das posicoes em aberto).

**Tres armadilhas encontradas, todas tratadas:**

1. **A data do arquivo nao e a data do dado.** O arquivo de 30/10 diz, no
   proprio texto, "acumulados ate o dia 28/10". O de 02/10 traz 30/09 - ou
   seja, ainda o mes anterior. O codigo le essa data do texto.
2. **Os valores sao acumulados no mes, nao diarios.** O fluxo de um dia e a
   diferenca para o pregao anterior, e isso so vale dentro do mesmo mes.
   Conferencia: a soma dos diarios de outubro deu 8,59 bi, contra 8,585 bi
   do acumulado que a B3 publica direto.
3. **Os nomes internos das colunas estao desalinhados com o conteudo.** Na
   participacao dos investidores, a coluna chamada "Sales" e a de
   porcentagem e as vendas estao em "Partmil". O codigo casa pelo rotulo
   visivel, nao pelo nome interno.

**Bloco 4.8 confirmado sem fonte.** O quadro analitico traz contratos em
aberto POR CONTRATO (WIN: 1.281.259 em 30/10), nao por tipo de participante.
A divisao por participante nao esta no publico. Opcoes: trocar o bloco por
contratos em aberto de WIN e WDO (dado real, pergunta diferente), remover,
ou pagar.

- [ ] Decidir o que fazer com o 4.8.

### Acrescentado em 02/11/2026: 4.8 trocado por "Contratos em aberto"

A divisao por tipo de participante nao e publica. Em vez de manter um bloco
sem fonte, ele foi trocado por **contratos em aberto por contrato**, que a B3
publica no quadro analitico.

Mostra WIN, IND, WDO e DOL, com o total em aberto e a variacao em 5 pregoes.
O historico e nosso: a B3 so publica o dia, e `cache-b3/` acumula.

**A pergunta mudou, e a tela diz isso.** "Quem esta comprado" era sobre o
saldo de um grupo; "contratos em aberto" e o total do mercado, sem lado. O
texto do bloco explica a diferenca para ninguem ler uma coisa achando que e
a outra.

Primeira leitura (30/10, com o crash de 26/10 no meio da janela):
WIN +31,8%, DOL +58,6%, WDO +13,5%, IND +2,6% em 5 pregoes.

`pipeline/manuais.py` foi removido: sem CSV na B3, o leitor manual ficou sem
entrada. Esta no historico do Git.

### Acrescentado em 02/11/2026: termometro com 4 dos 7 componentes

`pipeline/termometro.py`. Cada componente vira percentil, a nota e a media
simples dos que existem.

**Com fonte (4):** momento (EWZ no lugar do Ibovespa), volatilidade
(VXEWZ/FRED), porto seguro (dolar PTAX/BCB) e fluxo estrangeiro (B3).

**Sem fonte (3), e ficam visiveis na tela com o motivo:**

- Amplitude das acoes: precisaria do historico das ~85 acoes do Ibovespa, e
  a cota gratuita da Alpha Vantage e de 25 consultas por DIA.
- Posicao do estrangeiro no WIN: a B3 nao publica por tipo de participante.
- Protecao (put/call de BOVA11): sem fonte gratuita.

Eles NAO entram na media: quatro notas reais valem mais que quatro reais e
tres inventadas. A tela mostra "nota feita com X dos 7", separando o que
nao tem fonte do que apenas falhou hoje.

**Duas concessoes forcadas pela fonte:**

1. `outputsize=full` da Alpha Vantage virou recurso pago. Sobram 100
   pregoes, entao o momento usa media de 50 (a especificacao pedia 125) e
   percentil sobre ~50 pontos. Marcado com * na tela.
2. O fluxo so tem ~21 pregoes publicados, logo o percentil dele sai sobre
   15 janelas, nao sobre um ano. Tambem marcado.

**Ontem / semana / mes:** nao da para recalcular o termometro do passado -
as fontes de hoje nao dizem como o fluxo estava ha um mes. Entao o arquivo
guarda a nota de cada dia e a comparacao comeca a existir amanha. Ate la,
travessao.

**Primeira leitura, 02/11:** nota 34 (Medo), com volatilidade 100, dolar 1 e
fluxo 0. O momento, testado a parte com dados reais do EWZ, daria 0.

Vale entender por que a volatilidade sozinha diz "calmaria" enquanto tudo o
mais grita panico: ela compara a VXEWZ com a media de 50 dias, e a media
esta inflada pelo proprio susto de 26/10. A VXEWZ caiu de 67,69 (22/10) para
36,38 (30/10). Nao e defeito do calculo, e uma propriedade de comparar com
media apos um pico - mas e bom saber antes de ler a nota como verdade.

- [ ] Guardar o historico diario da nota por tempo suficiente para o
      "ontem / semana / mes" ficar util.

### Acrescentado em 02/11/2026: memoria dos indicadores

`pipeline/historico.py` grava `historico/indicadores.csv` ao fim de cada
execucao. Formato longo:

    data;referencia;indicador;valor;unidade;fonte

`data` e o dia em que o painel rodou; `referencia` e o pregao a que o numero
se refere. Os dois diferem: o fluxo chega com dois dias uteis de atraso.
Para analisar serie, usar `referencia`.

Formato longo (uma linha por indicador) e nao largo (uma coluna por
indicador) de proposito: quando um indicador nasce ou morre - e ja morreu um
neste projeto - o arquivo continua valido e o passado continua significando
a mesma coisa. Em formato largo, cada mudanca exigiria reescrever o historico.

- So entra dado REAL. Exemplo e dado desatualizado ficam de fora, para a
  serie nao ter degraus que nao aconteceram no mercado.
- Rodar duas vezes no mesmo dia substitui as linhas do dia, nao duplica.
- O fluxo entra com os ~19 pregoes que a B3 publica de uma vez, nao so o
  ultimo: esperar um mes pelo que ja esta na mao seria bobagem.
- 4 KB no primeiro dia; cerca de 2 KB por dia dai em diante.
- Fica fora do Git (dado derivado da B3).

### Acrescentado em 02/11/2026: opcoes.net nao serve, mas a B3 serve

**opcoes.net.br esta descartado.** Nao tem API (a tabela vem dentro do HTML,
entao seria raspagem de pagina) e os termos de uso, secao 5, dizem:

    "O usuario concorda em acessar as informacoes e servicos disponibilizados
    pelo site unica e exclusivamente por meio de um navegador de internet
    tradicional, sendo proibido qualquer tipo de acesso automatizado para
    coleta de informacoes, realizacao de simulacoes ou qualquer outro tipo de
    interacao com o site."

Alem de mais explicito que o aviso da B3, ha uma diferenca de natureza: a
SYSMIDIA e uma empresa pequena cujo PRODUTO e justamente esse dado tratado,
vendido por assinatura. A B3 e a bolsa publicando dado de referencia do
mercado que ela propria opera.

**A B3 tem o dado, e melhor.** No Boletim Diario, capitulo Derivativos de
bolsa:

- `OpenPositionsEquities` ("Posicoes em aberto"): uma linha por instrumento,
  com contratos em aberto e a variacao. Inclui as series de opcoes.
  Cerca de 43 mil linhas por dia, em 86 paginas de 500 (o pageSize parece
  limitado a 500; 5000 foi recusado).
- `InstrumentsDerivatives` ("Cadastro de instrumentos"): onde deve estar o
  strike de cada serie, que e o que falta para montar GEX e os muros.

- [ ] Conferir se o cadastro de instrumentos traz strike e tipo (call/put).
- [ ] Ver se da para filtrar por ativo em vez de baixar as 86 paginas.

### Acrescentado em 02/11/2026: opcoes de BOVA11, pela B3

`pipeline/opcoes.py`. Tres tabelas do Boletim Diario que se completam:

| Tabela | O que da | Paginas |
|---|---|---|
| `OpenPositionsEquities` | posicoes em aberto por serie | 43 |
| `InstrumentsEquities` | strike, tipo e vencimento da serie | 81 |
| `ConsolidatedTradesEquities` | fechamento do ativo e das opcoes | 74 |

**Tres descobertas que mudam o codigo:**

1. **Para opcao, "Contratos em aberto" vem VAZIA.** O numero esta em
   "Total de posicoes". Ler a coluna de nome obvio daria uma tabela
   inteira de zeros, sem erro nenhum na tela.
2. **Nao da para filtrar no servidor.** O campo "Digite o ticker desejado"
   do site da B3 filtra no NAVEGADOR, sobre as cem linhas ja carregadas.
   Entao e preciso varrer as paginas e filtrar aqui. A rota `/filters`
   responde 204 para estas tabelas.
3. **O cadastro nao muda.** O strike da BOVAK240W2 e o mesmo todo dia,
   entao ele e guardado para sempre em `cache-b3/cadastro-opcoes.json` e
   as 81 paginas so sao varridas quando aparece serie desconhecida.

**Para incluir outro ativo:** uma linha na lista `ATIVOS`, no topo de
`opcoes.py`. O `codigo` e o que a B3 escreve na coluna "Ativo"
("BOVA" para BOVA11, "PETR" para PETR4). A coleta ja traz todos; a pagina
mostra o primeiro, porque tem um bloco so.

**Duas honestidades na tela:**

- **Uma volatilidade so para todos os strikes**, tirada do VXEWZ, em vez da
  implicita de cada serie. Isso achata o sorriso e subestima o gamma das
  pontas. O premio de cada opcao esta no boletim (tabela de negocios
  consolidados), entao da para melhorar.
- **Sem conversao para pontos do Ibovespa**: exigiria o nivel do indice,
  que nao temos de fonte livre. Os niveis aparecem em reais, e a nota
  explica. `razao_ibov` fica nulo em vez de um numero inventado.

- [ ] Calcular a volatilidade implicita de cada serie a partir do premio.
- [ ] Achar o nivel do Ibovespa para voltar com a conversao em pontos.

### Correcoes de 02/11/2026 nas opcoes, depois de testar

Tres defeitos que so apareceram com dado real:

1. **O vencimento escolhido estava errado.** Pegava o mais proximo; o certo
   e o que concentra posicao. Medido: o semanal de 06/11 tinha 4,9 milhoes
   de contratos e o mensal de 19/11, 137 milhoes - vinte e oito vezes mais.
2. **O preco do BOVA11 nao esta na tabela de negocios consolidados**, que
   traz as opcoes e um punhado de papeis, mas nao ETFs. Esta na tabela
   IOPV, com UMA pagina de 70 linhas. Isso derrubou 74 paginas do custo
   diario, que caiu para 44.
3. **O cadastro era varrido em toda execucao.** Agora e no maximo uma vez
   por dia, com a data da ultima varredura guardada.

**Buraco conhecido, visivel na tela:** 448 series com posicao em aberto
real - uma delas com 10,3 milhoes de contratos - nao aparecem no cadastro
de instrumentos do mesmo pregao, nem no de equities nem no de derivativos.
Sem strike nao da para desenhar. O grafico cobre 57,6% das posicoes e diz
isso na tela. Como o cadastro e acumulado em disco, a cobertura tende a
melhorar sozinha conforme essas series aparecam em algum pregao.

Primeira leitura real (30/10, BOVA11 a 165,33, vencimento 19/11):
call wall 172, put wall 164, GEX +R$ 29,4 mi.

- [ ] Entender por que a B3 informa posicao em serie que o cadastro dela
      nao lista.

### Acrescentado em 02/11/2026: volatilidade implicita por serie

O gamma deixou de usar uma volatilidade unica. Agora cada serie tem a sua,
tirada do premio de fechamento dela por Black-Scholes invertido
(`calculos.volatilidade_implicita`, bisseccao).

Bisseccao e nao Newton-Raphson: e mais lenta, mas nao diverge. Divergir
aqui produziria um numero absurdo com cara de resposta.

Devolve nulo quando nao ha resposta sensata - premio abaixo do valor
intrinseco (premio velho de serie que nao negociou), premio zero, ou
volatilidade encostando no teto da busca.

**O que os numeros reais mostraram (30/10, vencimento 19/11):**

- Calls entre 19% e 22%; puts entre 23% e 25%. Put mais cara que call no
  mesmo strike e o skew classico de renda variavel - bom sinal de que a
  conta esta certa.
- **O VXEWZ, que era a volatilidade unica, marcava 36,4%** contra ~21% do
  mercado real de BOVA11. Nao e erro do VXEWZ: ele e do EWZ, cotado em
  dolar, e carrega a volatilidade do cambio junto. Como proxy de
  volatilidade de opcao brasileira, estava 70% acima.
- A reserva para serie que nao negociou passou a ser a **mediana das
  series negociadas na janela do grafico** (22,1%). A mediana de TODAS as
  series do vencimento daria 27,6%, puxada pelas asas do sorriso.

**Defeito corrigido junto:** a busca do gamma flip varria de 110 a 140,
faixa fixa herdada do exemplo. Com o BOVA11 a 165 ela nunca achava nada, e
o painel mostrava "—" como se nao houvesse flip. Agora a faixa acompanha o
preco (85% a 115%).

Leitura final: call wall 172, put wall 164, gamma flip 156,95,
GEX +R$ 49,3 mi.

- [ ] Black-Scholes nao considera dividendos. O BOVA11 distribui pouco,
      mas isso empurra a volatilidade das calls para baixo e a das puts
      para cima.

### Acrescentado em 03/11/2026: resumo do dia sem IA

A especificacao (4.2) previa mandar os numeros ao Claude e pedir tres
frases. Isso exige chave de API paga, e a regra do projeto e perguntar
antes de contratar servico. Entao o resumo passou a ser montado dos
proprios numeros do painel, em `pipeline/resumo.py`.

Tem uma vantagem que nao e pequena: texto montado de numero nao inventa.
Um modelo pode escrever "o minerio firme ajuda a Vale" sem que o minerio
tenha subido; aqui, se esta escrito que caiu, caiu. A desvantagem e ser
mais seco e nao conectar assuntos como uma pessoa conectaria.

As tres linhas: Nova York e o EWZ; dolar, petroleo e China; fluxo
estrangeiro e termometro. Movimento abaixo de 0,3% vira "de lado", para
nao dar adjetivo a ruido.

O campo `por_ia: false` fica no arquivo. Se um dia entrar a versao com
Claude, a tela sabe qual e qual - e o selo "Leitura por IA" so aparece
quando for verdade.

- [ ] Decidir se vale pagar API do Claude para a versao escrita.

### Teste do dia 03/11: o que o dia novo revelou

Rodar o pipeline num dia diferente testou o cache e achou um defeito:

- **Opcoes pedia o boletim de hoje**, que a B3 so publica depois das 15h,
  e falhava de manha. Agora recua ate achar um pregao publicado.
- Termometro subiu para 4 de 7 componentes (a cota da Alpha Vantage
  renova a cada dia) e a nota caiu de 34 para 26.
- Fluxo chegou aos 20 pregoes do grafico.
- Cache funcionou: o que ja tinha sido baixado ontem nao foi pedido de novo.
