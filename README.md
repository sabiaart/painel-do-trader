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

## Fase atual

Fase 0: base do projeto. Repositorio e estrutura de pastas prontos.

Pendente na Fase 0: repositorio no GitHub, deploy no Cloudflare Pages e dominio provisorio.
