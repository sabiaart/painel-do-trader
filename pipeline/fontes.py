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
from datetime import date, datetime, timedelta, timezone

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


def alpha_serie(simbolo: str, chave: str, *, minimo: int = 90) -> list[tuple[date, float]]:
    """Fechamentos diarios de um papel, do mais antigo para o mais novo.

    Sao 100 pregoes, e nao mais: `outputsize=full` virou recurso pago na
    Alpha Vantage. Quem chama precisa dimensionar media movel e percentil
    para caber nisso - o termometro usa media de 50 em vez dos 125 que a
    especificacao pedia, e diz isso na tela.
    """
    from urllib.parse import urlencode

    url = f"{ALPHA}?" + urlencode(
        {
            "function": "TIME_SERIES_DAILY",
            "symbol": simbolo,
            "outputsize": "compact",
            "apikey": chave,
        }
    )
    try:
        bruto = json.loads(baixar(url).decode("utf-8"))
    except json.JSONDecodeError as erro:
        raise FonteIndisponivel(f"{simbolo}: série não é JSON ({erro})") from erro

    for campo in ("Note", "Information", "Error Message"):
        if campo in bruto:
            raise FonteIndisponivel(f"{simbolo}: {str(bruto[campo])[:160]}")

    serie_bruta = bruto.get("Time Series (Daily)") or {}
    serie: list[tuple[date, float]] = []
    for dia, valores in serie_bruta.items():
        try:
            serie.append((date.fromisoformat(dia), float(valores["4. close"])))
        except (KeyError, ValueError):
            continue

    if len(serie) < minimo:
        raise FonteIndisponivel(f"{simbolo}: só {len(serie)} pregões, preciso de {minimo}")
    serie.sort()
    return serie


BRAPI = "https://brapi.dev/api/v2/futures"
LETRAS_MES = "FGHJKMNQUVXZ"  # codigo de vencimento da B3: F=jan ... Z=dez


def _brapi(caminho: str, parametros: dict) -> dict:
    """Chama a brapi. Os contratos WIN e WDO nao precisam de token.

    Atencao (registrado na secao 10 da especificacao): a brapi declara nao
    ser distribuidora licenciada da B3. Serve para o painel pessoal; para um
    site publico a licenca continua em aberto.
    """
    from urllib.parse import urlencode

    url = f"{BRAPI}/{caminho}?" + urlencode(parametros)
    try:
        resposta = json.loads(baixar(url).decode("utf-8"))
    except json.JSONDecodeError as erro:
        raise FonteIndisponivel(f"brapi {caminho}: resposta nao e JSON ({erro})") from erro
    if isinstance(resposta, dict) and resposta.get("error"):
        raise FonteIndisponivel(f"brapi {caminho}: {resposta.get('message')}")
    return resposta


def futuros_vigentes() -> dict[str, dict]:
    """Contrato de WIN e de WDO em vigor hoje.

    Em vez de reimplementar as regras de vencimento da B3 (que diferem entre
    os dois e mudam com feriado), pergunta por varios codigos de uma vez e
    fica com o de vencimento mais proximo que ainda nao passou. Se a regra
    mudar, isto continua certo.
    """
    hoje = date.today()
    candidatos = []
    for passo in range(10):
        mes = (hoje.month - 1 + passo) % 12
        ano = hoje.year + (hoje.month - 1 + passo) // 12
        candidatos.append(f"WIN{LETRAS_MES[mes]}{ano % 100:02d}")
        candidatos.append(f"WDO{LETRAS_MES[mes]}{ano % 100:02d}")

    dados = _brapi("quote", {"symbols": ",".join(candidatos[:20])})
    cotacoes = dados.get("quotes") or []
    if not cotacoes:
        raise FonteIndisponivel("brapi nao devolveu nenhum contrato futuro")

    vigentes: dict[str, dict] = {}
    for cotacao in sorted(cotacoes, key=lambda c: c.get("expirationDate") or ""):
        ativo = cotacao.get("underlyingAsset")
        if ativo not in ("WIN", "WDO") or ativo in vigentes:
            continue
        try:
            vencimento = date.fromisoformat(cotacao["expirationDate"])
        except (KeyError, ValueError):
            continue
        if vencimento < hoje:
            continue  # ja venceu
        if cotacao.get("settlement") is None:
            continue  # sem ajuste nao da para centrar a faixa
        vigentes[ativo] = cotacao

    faltando = {"WIN", "WDO"} - vigentes.keys()
    if faltando:
        raise FonteIndisponivel(f"nao achei contrato vigente de {', '.join(sorted(faltando))}")
    return vigentes


def futuro_historico(simbolo: str, dias: int = 200) -> list[dict]:
    """Serie diaria de um contrato: ajuste, maxima e minima, do mais antigo
    para o mais novo. Dias sem ajuste sao descartados."""
    from datetime import timedelta

    inicio = date.today() - timedelta(days=dias)
    dados = _brapi(
        "historical",
        {"symbol": simbolo, "startDate": inicio.isoformat(), "sortOrder": "asc"},
    )
    bruto = (dados.get("future") or {}).get("history") or []

    serie = []
    for ponto in bruto:
        ajuste = ponto.get("settlement")
        if not ajuste:
            continue
        try:
            dia = datetime.fromtimestamp(ponto["date"], tz=timezone.utc).date()
        except (KeyError, TypeError, ValueError, OSError):
            continue
        serie.append(
            {
                "data": dia,
                "ajuste": float(ajuste),
                "maxima": float(ponto["high"]) if ponto.get("high") else None,
                "minima": float(ponto["low"]) if ponto.get("low") else None,
            }
        )

    if len(serie) < 25:
        raise FonteIndisponivel(f"{simbolo}: só {len(serie)} pregões no histórico")
    return serie


def dolar_ptax(dias: int = 400) -> list[tuple[date, float]]:
    """Dolar PTAX de venda, diario."""
    return bcb_serie(SERIE_DOLAR, dias=dias)


def vol_ewz() -> list[tuple[date, float]]:
    """Indice de volatilidade das opcoes do EWZ (Cboe), em % ao ano."""
    return fred_serie("VXEWZCLS")
