# Painel do Trader

Site gratuito de contexto do mercado brasileiro para quem opera mini indice (WIN) e mini dolar (WDO).

Conteudo informativo. Nao e recomendacao de investimento.

## Estrutura

| Pasta | O que guarda |
|---|---|
| `site/` | As paginas do site (HTML, CSS e JavaScript) |
| `pipeline/` | Os scripts Python que baixam os dados e fazem as contas |
| `data/` | Os arquivos JSON gerados pelo pipeline. O site so le daqui |
| `prototipo/` | A referencia visual (`painel-trader.html`) |
| `.github/workflows/` | Os agendamentos do robo |

## Documentos

- `ESPECIFICACAO.md` — a especificacao completa do projeto. Ler antes de qualquer tarefa nova.
- `CLAUDE.md` — as regras de trabalho.

## O site e privado

Enquanto for so do dono, o painel fica atras de usuario e senha. Isso nao e
capricho: as licencas dos dados de mercado valem para uso pessoal, e um
endereco aberto na internet nao se enquadra nisso.

A trava esta em `worker/index.js`. A senha NAO fica no codigo: fica nos
segredos do Cloudflare, nos nomes `PAINEL_USUARIO` e `PAINEL_SENHA`. Por isso
este repositorio pode continuar publico.

Se os segredos nao estiverem cadastrados, o site responde "nao configurado" e
nao mostra nada. Ele falha trancado, nunca destrancado.

Para abrir o site ao publico um dia, apague `main` e `run_worker_first` do
`wrangler.jsonc` - e antes disso resolva as licencas da secao 10 da
especificacao.

## Fase atual

Fase 0: base do projeto. Repositorio e estrutura de pastas prontos.

Pendente na Fase 0: repositorio no GitHub, deploy no Cloudflare Pages e dominio provisorio.
