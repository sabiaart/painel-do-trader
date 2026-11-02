# site/data/

Os JSON que o site le. Quem escreve aqui e o pipeline, nunca a mao.

Esta pasta fica dentro de `site/` porque so o que esta em `site/` vai para o ar.
E a mesma pasta `data/` descrita na especificacao, so que no lugar publicado.

Regras:

- Todo arquivo tem `gerado_em` (data e hora), `origem` (de onde veio o dado) e
  `exemplo` (true ou false).
- Enquanto `exemplo` for `true`, a tela avisa que o dado e de exemplo.
- Se uma fonte falhar, o pipeline mantem o arquivo anterior e nao sobrescreve
  com dado vazio.
