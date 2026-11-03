"""Resumo do dia, montado dos numeros que o painel ja tem.

Por que nao e IA
----------------
A especificacao previa mandar os dados ao Claude e pedir tres frases. Isso
exige chave de API paga, e a regra do projeto e perguntar antes de
contratar servico. Enquanto nao houver essa decisao, o resumo sai daqui:
frases montadas a partir dos mesmos numeros que estao na tela.

Tem uma vantagem que nao e pequena: texto montado de numero nao inventa.
Um modelo de linguagem pode escrever "o minerio firme ajuda a Vale" sem
que o minerio tenha subido; aqui, se esta escrito que caiu, caiu.

E tem a desvantagem obvia: e mais seco e nao conecta assuntos como uma
pessoa conectaria.

Regra que vale para as duas versoes
-----------------------------------
Nada de recomendacao, nada de previsao de preco. So descrever o que os
numeros dizem, no passado ou no presente. Nunca no futuro.
"""

from __future__ import annotations

import comum

# Quanto um movimento precisa ter para merecer adjetivo. Abaixo disso a
# variacao e ruido e o texto diz "de lado".
FORTE = 1.5
LEVE = 0.3


def _tom(variacao: float) -> str:
    """Como descrever um movimento, sem exagerar nem minimizar."""
    tamanho = abs(variacao)
    if tamanho < LEVE:
        return "de lado"
    direcao = "alta" if variacao > 0 else "queda"
    if tamanho >= FORTE:
        return f"{direcao} forte"
    return direcao


def _pct(variacao: float) -> str:
    return f"{abs(variacao):.2f}".replace(".", ",") + "%"


def _maiuscula(frase: str) -> str:
    """So a primeira letra. `str.capitalize()` rebaixa o resto e estraga
    "China" e "R$", que viram "china" e "r$"."""
    return frase[:1].upper() + frase[1:] if frase else frase


def _acha(ativos: list[dict], pedaco: str) -> dict | None:
    for ativo in ativos:
        if pedaco.lower() in ativo.get("nome", "").lower():
            return ativo
    return None


def _linha_nova_york(ativos: list[dict]) -> str | None:
    spy = _acha(ativos, "S&P 500")
    ewz = _acha(ativos, "Brasil")
    if not spy or not ewz:
        return None

    movimento = _tom(spy["variacao"])
    if movimento == "de lado":
        inicio = f"Nova York fechou de lado, com o S&P 500 em {_pct(spy['variacao'])}"
    else:
        verbo = "subiu" if spy["variacao"] > 0 else "caiu"
        inicio = f"Nova York {verbo} {_pct(spy['variacao'])} no S&P 500"

    # O EWZ merece a mesma frase porque e o termometro de Brasil la fora.
    junto = (ewz["variacao"] > 0) == (spy["variacao"] > 0)
    ligacao = "e" if junto else "mas"
    verbo_ewz = "subiu" if ewz["variacao"] > 0 else "caiu"
    return f"{inicio}, {ligacao} o EWZ, que segue o Brasil, {verbo_ewz} {_pct(ewz['variacao'])}."


def _linha_commodities(ativos: list[dict]) -> str | None:
    dolar = _acha(ativos, "Dólar")
    brent = _acha(ativos, "Brent")
    china = _acha(ativos, "China")
    pedacos = []

    if dolar:
        verbo = "subiu" if dolar["variacao"] > 0 else "recuou"
        pedacos.append(f"o dólar {verbo} {_pct(dolar['variacao'])}")
    if brent:
        verbo = "subiu" if brent["variacao"] > 0 else "caiu"
        pedacos.append(f"o petróleo {verbo} {_pct(brent['variacao'])}")
    if china and abs(china["variacao"]) >= LEVE:
        verbo = "subiu" if china["variacao"] > 0 else "caiu"
        pedacos.append(f"a China {verbo} {_pct(china['variacao'])}")

    if not pedacos:
        return None
    if len(pedacos) == 1:
        return _maiuscula(pedacos[0]) + "."
    return _maiuscula(", ".join(pedacos[:-1]) + " e " + pedacos[-1]) + "."


def _linha_contexto() -> str | None:
    """Fluxo estrangeiro e termometro: o contexto que o painel ja calculou."""
    pedacos = []

    fluxo = comum.ler("fluxo") or {}
    if not fluxo.get("exemplo") and fluxo.get("ontem") is not None:
        saldo = fluxo["ontem"]
        quando = (fluxo.get("pregao") or "")[8:10] + "/" + (fluxo.get("pregao") or "")[5:7]
        lado = "comprou" if saldo > 0 else "vendeu"
        valor = f"{abs(saldo):.2f}".replace(".", ",")
        pedacos.append(f"o estrangeiro {lado} R$ {valor} bi no pregão de {quando}")

    termometro = comum.ler("termometro") or {}
    if not termometro.get("exemplo") and termometro.get("nota") is not None:
        zona = str(termometro.get("zona", "")).lower()
        pedacos.append(f"e o termômetro está em {termometro['nota']}, zona de {zona}")

    if not pedacos:
        return None
    return _maiuscula(" ".join(pedacos)) + "."


def montar() -> dict:
    """Monta o resumo. Levanta FonteIndisponivel se nao houver dado real."""
    globais = comum.ler("globais") or {}
    if globais.get("exemplo"):
        raise comum.FonteIndisponivel("a grade de mercados ainda é exemplo")

    ativos = globais.get("ativos") or []
    linhas = [
        linha
        for linha in (_linha_nova_york(ativos), _linha_commodities(ativos), _linha_contexto())
        if linha
    ]
    if not linhas:
        raise comum.FonteIndisponivel("nenhum dado real para resumir")

    dados = comum.cabecalho("montado dos números do próprio painel")
    dados["linhas"] = linhas
    dados["pregao"] = globais.get("pregao")
    # A tela mostra um selo "Leitura por IA" no bloco de noticias. Aqui
    # nao: este texto nao passou por modelo nenhum, e dizer o contrario
    # seria mentira boba.
    dados["por_ia"] = False
    dados["desatualizado"] = bool(globais.get("desatualizado"))
    dados["fechamento"] = None
    return dados
