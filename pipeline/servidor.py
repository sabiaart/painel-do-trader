"""Servidor local do painel.

E o `python -m http.server` com uma diferenca importante: ele manda o
navegador NAO guardar nada em cache.

Sem isso, o navegador guarda o CSS e o JavaScript por horas e voce fica
vendo uma versao velha do painel depois de cada mudanca - inclusive
depois dos dados novos do dia.

    python pipeline/servidor.py [porta]
"""

from __future__ import annotations

import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SITE = RAIZ / "site"

PORTA_PADRAO = 8787


class SemCache(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, formato: str, *args) -> None:
        """Só registra o que deu errado. O painel faz dezenas de pedidos
        por carregamento e a janela viraria uma cachoeira de texto."""
        try:
            codigo = int(args[1])
        except (IndexError, ValueError):
            codigo = 0
        if codigo >= 400:
            sys.stderr.write(f"  [{codigo}] {args[0]}\n")


def main() -> int:
    porta = PORTA_PADRAO
    if len(sys.argv) > 1:
        try:
            porta = int(sys.argv[1])
        except ValueError:
            print(f"Porta inválida: {sys.argv[1]}")
            return 1

    if not (SITE / "index.html").exists():
        print(f"Não encontrei o site em {SITE}")
        return 1

    manipulador = partial(SemCache, directory=str(SITE))
    try:
        servidor = ThreadingHTTPServer(("127.0.0.1", porta), manipulador)
    except OSError as erro:
        print(f"Não consegui usar a porta {porta}: {erro}")
        print("Talvez o painel já esteja aberto noutra janela.")
        return 1

    # 127.0.0.1 e nao 0.0.0.0: o painel so responde neste computador,
    # ninguem na mesma rede alcanca.
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nPainel encerrado.")
    finally:
        servidor.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
