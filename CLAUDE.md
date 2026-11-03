# Painel do Trader

Site gratuito de contexto do mercado brasileiro para traders de WIN e WDO, monetizado com anúncios e afiliados.

- A especificação completa está em `ESPECIFICACAO.md`. Leia antes de qualquer tarefa nova.
- A referência visual é `prototipo/painel-trader.html`.
- Siga as fases da seção 8 da especificação, uma de cada vez.

## Regras do projeto

- **Painel pessoal, não site público.** Os dados ficam no computador e não são republicados. Decidido em 02/11/2026; a ideia de site com anúncios está parada.
- **A coleta da B3 é automatizada, contra os termos dela.** O dono leu o aviso ("é expressamente vedada a coleta automatizada, inclusive por meio de ferramentas de inteligência artificial, para quaisquer finalidades, comerciais ou não") e decidiu seguir assim, para uso pessoal. Não é para esconder isso: `pipeline/b3.py` abre com esse aviso escrito. Se um dia o painel for publicado, essa coleta sai antes.
- **Baixar uma vez por dia e guardar.** Nada de repetir pedido que já está em `cache-b3/`.
- **Nada de recomendação de investimento** em textos, gerados por IA ou não. Só estatística e contexto.
- Dados de exemplo sempre identificados como exemplo na tela.
- Se uma fonte falhar, mantenha o último dado válido com a data dele. A página nunca quebra.
- Celular primeiro: tudo precisa funcionar a 400px de largura.

## Como trabalhar comigo

- Não sou programador. Explique em português simples e em passos curtos.
- Pergunte antes de contratar serviço pago, criar contas ou publicar no domínio definitivo.
- Commits pequenos, com mensagens em português.
- Ao terminar uma fase, mostre o resultado e liste o que ficou pendente.
