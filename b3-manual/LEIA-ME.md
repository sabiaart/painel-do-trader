# Arquivos da B3 — download manual

Esta pasta é o único caminho pelo qual dados da B3 entram no painel.

**Por quê manual.** A B3 escreve nos termos do site dela que *"é expressamente
vedada a coleta automatizada, inclusive por meio de ferramentas de inteligência
artificial, para quaisquer finalidades, comerciais ou não, próprias ou de
terceiros"*. Então o robô deste projeto nunca acessa `b3.com.br`. Você baixa,
ele lê o que está no seu computador. Você clicando no site é uso normal; um
programa clicando por você não é.

---

## O que você faz, todo dia

1. Baixe os dois arquivos (abaixo).
2. Jogue cada um na pasta certa:
   - fluxo estrangeiro → `b3-manual/fluxo/`
   - posições por participante → `b3-manual/participantes/`
3. Dê dois cliques no `Painel.bat`, como sempre.

Não precisa renomear nada. Não precisa abrir no Excel. O leitor aceita
`.csv`, `.xlsx` e `.xlsm`, procura a data e os participantes **por palavra**,
em qualquer coluna — e imprime na tela preta de qual célula tirou cada número,
para você conferir contra a planilha.

Depois de ler, o arquivo é movido para `ja-lidos/`. Assim a pasta de entrada
fica sempre vazia e você vê de olho o que ainda falta baixar.

> Se o arquivo vier em `.xls` (formato antigo), abra no Excel e salve como
> `.xlsx`. Aquele formato é binário de 1997 e não dá para ler sem instalar
> biblioteca.

---

## Os dois dados estão no mesmo lugar

Desde 07/04/2025 a B3 juntou tudo no **Boletim Diário do Mercado**:

**[Boletim Diário do Mercado](https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/consultas/boletim-diario/dados-publicos-de-produtos-listados-e-de-balcao/)**

Baixe sempre em **CSV**, nunca em PDF — PDF eu não leio.
O site guarda só os **últimos 10 dias**, então o histórico se perde se você
ficar muito tempo sem baixar.

### Arquivo 1 — fluxo estrangeiro  ✅

Capítulo **Indicadores e Informativos**, tabela **Participação dos
Investidores**.

Traz compras e vendas por tipo de investidor, em **R$ mil**, cada uma com a
sua participação em porcento. Não tem coluna de saldo: o leitor calcula
compras menos vendas e ignora as colunas de porcentagem.

Jogue o arquivo em `b3-manual/fluxo/`. Vira o bloco **"Fluxo estrangeiro"**.

### Arquivo 2 — posições por participante  ⚠️

Capítulo **Cotações**, tabela **Resumo Estatístico**.

**Atenção: isto provavelmente não serve.** O Resumo Estatístico traz os
contratos em aberto **por contrato** (WINZ26, e assim por diante), e não
divididos por tipo de participante. Se for isso mesmo, o bloco "Quem está
comprado no WIN" como foi especificado não existe mais de graça.

Baixe assim mesmo e jogue em `b3-manual/participantes/`. Se a tabela tiver a
divisão por participante, o leitor acha; se não tiver, ele avisa e eu
reescrevo o bloco para mostrar outra coisa.

> **O link veio de um buscador, não do site da B3** — eu não acesso
> b3.com.br. Os capítulos e tabelas acima vieram do aviso que você me
> mostrou. Se a página não bater com isto, me diga o que apareceu.

---

## Histórico: por que ele existe

Cada download da B3 traz **um pregão**. O gráfico de fluxo mostra **vinte**.

Para você não ter que baixar vinte arquivos todo dia, o leitor guarda cada
pregão que já leu em `historico.json`, nesta pasta. O arquivo cresce um
pouquinho por dia e nunca é apagado sozinho.

Consequência honesta, que aparece na tela: nos primeiros dias o gráfico tem
menos de 20 barras, e os totais do mês e do ano somam **só os pregões que você
baixou** — não o ano inteiro da B3. O painel se marca como parcial enquanto
isso durar. Se quiser o histórico cheio de uma vez, baixe os arquivos dos dias
anteriores e jogue todos na pasta juntos: ele lê um por um, do mais antigo
para o mais novo.

## Se der erro

A tela preta diz qual arquivo e por quê. Os três casos comuns:

| O que aparece | O que fazer |
|---|---|
| `não achei a data do pregão` | Provavelmente é a planilha errada, ou um resumo mensal em vez do diário. |
| `não achei nenhum tipo de participante` | O leitor mostra a primeira linha do arquivo. Me mande essa linha que eu ajusto. |
| `formato .xls antigo` | Abra no Excel e salve como `.xlsx`. |

Erro aqui **não derruba o painel**. Os outros blocos atualizam normalmente e
estes dois continuam mostrando o último dado válido, com a data dele.

## O que NÃO vai para o GitHub

O conteúdo desta pasta fica só no seu computador: os arquivos da B3, a pasta
`ja-lidos` e o `historico.json`. Só este `LEIA-ME.md` é versionado. Os dados
da B3 são dela; redistribuí-los num repositório público seria outra conversa,
com outra licença.
