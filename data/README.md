# data/

Esta pasta guarda os JSON que o site le. Quem escreve aqui e o pipeline, nunca a mao.

Regras:

- Todo arquivo tem os campos `gerado_em` (data e hora), `origem` (de onde veio o dado) e `exemplo` (true ou false).
- Enquanto `exemplo` for `true`, a tela precisa avisar que o dado e de exemplo.
- Se uma fonte falhar, o pipeline mantem o arquivo anterior e nao sobrescreve com dado vazio.
