# Esta pasta não é mais necessária

O painel passou a buscar os dados da B3 sozinho, em 02/11/2026. Você não
precisa baixar nada.

O que era feito aqui à mão virou `pipeline/b3.py`, que conversa direto com a
API do Boletim Diário do Mercado e guarda cada pregão em `cache-b3/`.

**Leia o aviso no topo de `pipeline/b3.py` antes de mexer nisso.** A B3
proíbe coleta automatizada nos termos dela; a decisão de seguir assim foi
tomada com o texto à vista, vale para uso pessoal e sem republicação.

O leitor de planilhas que existia aqui (`pipeline/manuais.py`) foi removido:
ficou sem entrada, porque a B3 só publica PDF para download manual. Ele está
no histórico do Git se um dia fizer falta.

Pode apagar esta pasta e o que sobrou dentro dela.
