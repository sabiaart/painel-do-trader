"""De onde vem cada numero.

Fase 2 usa so fontes publicas, sem cadastro e sem duvida de licenca:

- Banco Central, sistema SGS: dolar PTAX de venda, serie 1.
  https://dadosabertos.bcb.gov.br  (dados abertos, uso livre com citacao)

- FRED, do Federal Reserve de St. Louis: VXEWZCLS, o indice de volatilidade
  das opcoes do EWZ, calculado pela Cboe.
  https://fred.stlouisfed.org/series/VXEWZCLS

Nenhuma das duas e raspagem: as duas publicam o arquivo para download.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import date, datetime, timedelta

from comum import FonteIndisponivel, baixar

SGS = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={serie}"

SERIE_DOLAR = 1  # dolar dos EUA (venda) - PTAX


def bcb_serie(codigo: int, *, dias: int = 400) -> list[tuple[date, float]]:
    """Serie diaria do SGS, do mais antigo para o mais novo.

    O SGS devolve data como 28/10/2026 e valor como texto ("5.3420"),
    sempre com ponto decimal, mesmo sendo brasileiro.
    """
    fim = date.today()
    inicio = fim - timedelta(days=dias)
    url = (
        SGS.format(codigo=codigo)
        + f"?formato=json&dataInicial={inicio:%d/%m/%Y}&dataFinal={fim:%d/%m/%Y}"
    )
    try:
        bruto = json.loads(baixar(url).decode("utf-8"))
    except json.JSONDecodeError as erro:
        raise FonteIndisponivel(f"SGS {codigo} devolveu algo que nao e JSON: {erro}") from erro

    serie: list[tuple[date, float]] = []
    for item in bruto:
        try:
            dia = datetime.strptime(item["data"], "%d/%m/%Y").date()
            serie.append((dia, float(item["valor"])))
        except (KeyError, ValueError):
            continue  # uma linha estranha nao invalida a serie inteira

    if len(serie) < 30:
        raise FonteIndisponivel(f"SGS {codigo} devolveu so {len(serie)} dias; esperado bem mais")
    serie.sort()
    return serie


def fred_serie(serie: str) -> list[tuple[date, float]]:
    """Serie diaria do FRED, do mais antigo para o mais novo.

    O CSV traz feriados e fins de semana com o valor em branco ou como ".".
    Esses dias sao descartados.
    """
    texto = baixar(FRED.format(serie=serie)).decode("utf-8")
    leitor = csv.reader(io.StringIO(texto))
    try:
        next(leitor)  # cabecalho
    except StopIteration as erro:
        raise FonteIndisponivel(f"FRED {serie} devolveu um arquivo vazio") from erro

    dados: list[tuple[date, float]] = []
    for linha in leitor:
        if len(linha) < 2:
            continue
        bruto = linha[1].strip()
        if bruto in ("", "."):
            continue
        try:
            dados.append((date.fromisoformat(linha[0].strip()), float(bruto)))
        except ValueError:
            continue

    if len(dados) < 30:
        raise FonteIndisponivel(f"FRED {serie} devolveu so {len(dados)} dias uteis")
    dados.sort()
    return dados


ALPHA = "https://www.alphavantage.co/query"


class SemChave(Exception):
    """Falta a chave de API. Nao e erro de rede: e configuracao."""


def alpha_cotacao(simbolo: str, chave: str) -> dict:
    """Cotacao de um papel na Alpha Vantage.

    Devolve preco, fechamento anterior, variacao em % e a data do pregao.

    O plano gratuito e de 25 consultas por dia. Quando estoura, a resposta
    vem 200 com um aviso em vez de dados - por isso a checagem abaixo.
    """
    from urllib.parse import urlencode

    url = f"{ALPHA}?" + urlencode(
        {"function": "GLOBAL_QUOTE", "symbol": simbolo, "apikey": chave}
    )
    try:
        bruto = json.loads(baixar(url).decode("utf-8"))
    except json.JSONDecodeError as erro:
        raise FonteIndisponivel(f"{simbolo}: resposta nao e JSON ({erro})") from erro

    # Limite diario estourado, ou chave recusada.
    for campo in ("Note", "Information", "Error Message"):
        if campo in bruto:
            raise FonteIndisponivel(f"{simbolo}: {str(bruto[campo])[:160]}")

    cotacao = bruto.get("Global Quote") or {}
    if not cotacao:
        raise FonteIndisponivel(f"{simbolo}: resposta sem cotação")

    try:
        preco = float(cotacao["05. price"])
        anterior = float(cotacao["08. previous close"])
        dia = date.fromisoformat(cotacao["07. latest trading day"])
    except (KeyError, ValueError) as erro:
        raise FonteIndisponivel(f"{simbolo}: campos faltando ({erro})") from erro

    if preco <= 0 or anterior <= 0:
        raise FonteIndisponivel(f"{simbolo}: preço zerado")

    return {
        "simbolo": simbolo,
        "preco": preco,
        "anterior": anterior,
        "variacao": (preco / anterior - 1) * 100,
        "data": dia,
    }


def dolar_ptax(dias: int = 400) -> list[tuple[date, float]]:
    """Dolar PTAX de venda, diario."""
    return bcb_serie(SERIE_DOLAR, dias=dias)


def vol_ewz() -> list[tuple[date, float]]:
    """Indice de volatilidade das opcoes do EWZ (Cboe), em % ao ano."""
    return fred_serie("VXEWZCLS")
