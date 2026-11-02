"""As contas do painel.

Tudo aqui e estatistica descritiva. Nada neste arquivo preve preco nem
sugere operacao.
"""

from __future__ import annotations

import math
from datetime import date

PREGOES_NO_ANO = 252


def retornos_log(precos: list[float]) -> list[float]:
    """Variacao diaria em log. E o padrao para medir volatilidade:
    somar variacoes em log de varios dias da a variacao do periodo."""
    saida = []
    for anterior, atual in zip(precos, precos[1:]):
        if anterior > 0 and atual > 0:
            saida.append(math.log(atual / anterior))
    return saida


def volatilidade_historica(precos: list[float], janela: int = 21) -> float:
    """Volatilidade anualizada, em fracao (0,17 = 17% ao ano).

    Desvio padrao dos retornos diarios dos ultimos `janela` pregoes,
    multiplicado por raiz de 252 para virar medida anual.

    21 pregoes e cerca de um mes: reage a mudanca de regime sem virar
    ruido puro.
    """
    rets = retornos_log(precos)[-janela:]
    if len(rets) < 5:
        raise ValueError(f"preciso de pelo menos 5 retornos, recebi {len(rets)}")
    media = sum(rets) / len(rets)
    variancia = sum((r - media) ** 2 for r in rets) / (len(rets) - 1)
    return math.sqrt(variancia) * math.sqrt(PREGOES_NO_ANO)


def movimento_esperado(preco: float, vol_anual: float) -> float:
    """Movimento de 1 desvio para um pregao.

        movimento = preco x volatilidade anual x raiz(1/252)

    Cobre cerca de 68% dos dias. Dois desvios cobrem cerca de 95%.
    Nao e teto nem piso: e a frequencia com que algo aconteceu no passado.
    """
    return preco * vol_anual * math.sqrt(1 / PREGOES_NO_ANO)


def percentil(valor: float, historico: list[float]) -> int:
    """Em que percentil dos ultimos valores este numero esta (0 a 100)."""
    if not historico:
        raise ValueError("historico vazio")
    abaixo = sum(1 for h in historico if h < valor)
    return round(abaixo / len(historico) * 100)


def faixa_respeitada(serie: list[dict], janela: int = 30, vol_janela: int = 21) -> tuple[int, int]:
    """Em quantos dos ultimos pregoes o preco ficou dentro de 1 desvio.

    `serie` e a lista de pregoes, do mais antigo para o mais novo, com
    `ajuste`, `maxima` e `minima`.

    Para cada dia, refaz a conta como ela teria sido feita NAQUELE dia:
    pega o ajuste do dia anterior e a volatilidade dos pregoes ate ali.
    Usar a volatilidade de hoje para julgar o passado inflaria o acerto.

    Devolve (acertos, total_avaliado).
    """
    acertos = 0
    avaliados = 0

    # Comeca onde ja existe historico suficiente para medir volatilidade.
    primeiro = max(vol_janela + 1, len(serie) - janela)
    for i in range(primeiro, len(serie)):
        dia = serie[i]
        if dia["maxima"] is None or dia["minima"] is None:
            continue
        anteriores = [d["ajuste"] for d in serie[: i]]
        try:
            vol = volatilidade_historica(anteriores, vol_janela)
        except ValueError:
            continue
        centro = serie[i - 1]["ajuste"]
        desvio = movimento_esperado(centro, vol)
        avaliados += 1
        if dia["maxima"] <= centro + desvio and dia["minima"] >= centro - desvio:
            acertos += 1

    return acertos, avaliados


def variacao_percentual(serie: list[tuple[date, float]]) -> float:
    """Variacao do ultimo valor contra o anterior, em porcento."""
    if len(serie) < 2:
        raise ValueError("preciso de pelo menos dois valores")
    anterior, atual = serie[-2][1], serie[-1][1]
    return (atual / anterior - 1) * 100
