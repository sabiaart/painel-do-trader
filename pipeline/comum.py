"""Pecas que todo coletor do pipeline usa.

A regra mais importante deste arquivo esta em `gravar`: se uma fonte falhar,
o arquivo anterior fica como esta. O site nunca recebe dado vazio e nunca
quebra por causa de uma fonte fora do ar.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "site" / "data"

FUSO_BR = timezone(timedelta(hours=-3))
AGENTE = "painel-do-trader/1.0 (+https://github.com/sabiaart/painel-do-trader)"


class FonteIndisponivel(Exception):
    """A fonte nao respondeu ou respondeu algo que nao da para usar."""


def agora() -> str:
    """Data e hora de Brasilia, no formato que os JSON usam."""
    return datetime.now(FUSO_BR).isoformat(timespec="seconds")


def baixar(url: str, *, tentativas: int = 3, espera: float = 3.0) -> bytes:
    """Baixa uma URL. Tenta de novo algumas vezes antes de desistir.

    Falhas de rede sao comuns e passageiras; desistir na primeira seria
    jogar fora um dado que viria na segunda tentativa.
    """
    ultimo_erro: Exception | None = None
    for tentativa in range(1, tentativas + 1):
        try:
            pedido = urllib.request.Request(url, headers={"User-Agent": AGENTE})
            with urllib.request.urlopen(pedido, timeout=30) as resposta:
                if resposta.status != 200:
                    raise FonteIndisponivel(f"HTTP {resposta.status}")
                return resposta.read()
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as erro:
            ultimo_erro = erro
            if tentativa < tentativas:
                time.sleep(espera * tentativa)
    raise FonteIndisponivel(f"{url} nao respondeu: {ultimo_erro}")


def ler(nome: str) -> dict | None:
    """Le um JSON que ja esta em site/data/. Devolve None se nao existir."""
    caminho = DADOS / f"{nome}.json"
    if not caminho.exists():
        return None
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def gravar(nome: str, dados: dict) -> None:
    """Grava um JSON em site/data/.

    Escreve primeiro num arquivo temporario e so depois troca pelo definitivo.
    Assim, se o processo morrer no meio, o site continua lendo a versao
    anterior inteira em vez de meio arquivo.
    """
    DADOS.mkdir(parents=True, exist_ok=True)
    caminho = DADOS / f"{nome}.json"
    temporario = caminho.with_suffix(".json.tmp")
    texto = json.dumps(dados, ensure_ascii=False, indent=1, sort_keys=False)
    temporario.write_text(texto + "\n", encoding="utf-8", newline="\n")
    temporario.replace(caminho)


def manter_anterior(nome: str, motivo: str) -> dict | None:
    """Chamado quando uma fonte falha.

    Nao sobrescreve nada. So marca no arquivo que ele ficou velho e por que,
    para a tela poder avisar "dado de [data]".
    """
    anterior = ler(nome)
    if anterior is None:
        print(f"  ! {nome}: fonte falhou e nao ha dado anterior ({motivo})")
        return None
    anterior["desatualizado"] = True
    anterior["motivo_falha"] = motivo
    anterior["verificado_em"] = agora()
    gravar(nome, anterior)
    print(f"  ! {nome}: fonte falhou, mantido o dado de {anterior.get('gerado_em')} ({motivo})")
    return anterior


def chave(nome: str) -> str | None:
    """Le uma chave de API.

    Procura em dois lugares, nesta ordem:

    1. Variavel de ambiente - e assim que o robo do GitHub recebe a chave,
       a partir dos segredos do repositorio.
    2. Arquivo `chaves.env` na raiz do projeto - e assim no seu computador.

    O `chaves.env` esta no .gitignore e NUNCA vai para o GitHub. O formato
    dele e uma linha por chave:

        ALPHA_VANTAGE=suachaveaqui

    Devolve None quando a chave nao existe. Quem chamou decide o que fazer:
    nenhum bloco do painel pode quebrar so porque falta uma chave.
    """
    import os

    valor = os.environ.get(nome)
    if valor:
        return valor.strip()

    arquivo = RAIZ / "chaves.env"
    if not arquivo.exists():
        return None
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        k, _, v = linha.partition("=")
        if k.strip() == nome:
            return v.strip().strip('"').strip("'") or None
    return None


def cabecalho(origem: str, *, exemplo: bool = False) -> dict:
    """Os campos que todo arquivo de dados precisa ter."""
    return {
        "gerado_em": agora(),
        "origem": origem,
        "exemplo": exemplo,
        "desatualizado": False,
    }
