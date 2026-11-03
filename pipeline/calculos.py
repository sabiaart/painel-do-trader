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


def _normal_acumulada(x: float) -> float:
    """Probabilidade de a normal padrao ficar abaixo de x."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def preco_black_scholes(
    tipo: str, preco: float, strike: float, prazo: float, juros: float, vol: float
) -> float:
    """Preco teorico de uma opcao europeia.

    As opcoes de BOVA11 sao europeias (o cadastro da B3 diz "EURO"), entao
    Black-Scholes serve. Para opcao americana isto seria so uma aproximacao.

    Nao considera dividendos. O BOVA11 distribui pouco, mas isso empurra a
    volatilidade das calls um pouco para baixo e a das puts para cima.
    """
    if prazo <= 0 or vol <= 0 or preco <= 0 or strike <= 0:
        raise ValueError("preço, strike, prazo e volatilidade precisam ser positivos")

    vt = vol * math.sqrt(prazo)
    d1 = (math.log(preco / strike) + (juros + vol * vol / 2) * prazo) / vt
    d2 = d1 - vt
    desconto = strike * math.exp(-juros * prazo)

    if tipo == "call":
        return preco * _normal_acumulada(d1) - desconto * _normal_acumulada(d2)
    return desconto * _normal_acumulada(-d2) - preco * _normal_acumulada(-d1)


def volatilidade_implicita(
    tipo: str,
    premio: float,
    preco: float,
    strike: float,
    prazo: float,
    juros: float,
) -> float | None:
    """Que volatilidade faz Black-Scholes dar o premio observado.

    Nao ha formula: procura-se o valor por tentativa. Usamos bisseccao, que
    e mais lenta que Newton-Raphson mas nao diverge - e divergir aqui
    produziria um numero absurdo com cara de resposta.

    Devolve None quando nao existe resposta sensata, que acontece bastante:
    serie sem negocio no dia fica com premio velho, e premio abaixo do
    valor intrinseco nao vem de volatilidade nenhuma.
    """
    if premio <= 0 or prazo <= 0 or preco <= 0 or strike <= 0:
        return None

    # Abaixo do valor intrinseco nao ha volatilidade que explique: seria
    # arbitragem. Normalmente e premio desatualizado.
    desconto = strike * math.exp(-juros * prazo)
    intrinseco = max(preco - desconto, 0) if tipo == "call" else max(desconto - preco, 0)
    if premio < intrinseco - 1e-9:
        return None

    baixo, alto = 1e-4, 5.0
    try:
        if preco_black_scholes(tipo, preco, strike, prazo, juros, alto) < premio:
            return None  # nem 500% de volatilidade explica o premio
    except ValueError:
        return None

    for _ in range(80):
        meio = (baixo + alto) / 2
        try:
            teorico = preco_black_scholes(tipo, preco, strike, prazo, juros, meio)
        except ValueError:
            return None
        if teorico > premio:
            alto = meio
        else:
            baixo = meio
        if alto - baixo < 1e-6:
            break

    vol = (baixo + alto) / 2
    # Encostou no teto ou no chao da busca: nao e resposta, e desistencia.
    if vol <= 1e-3 or vol >= 4.99:
        return None
    return vol


def media_movel(valores: list[float], janela: int) -> list[float | None]:
    """Media dos ultimos `janela` valores, em cada ponto da serie.

    Devolve uma lista do mesmo tamanho da entrada, com None nos primeiros
    pontos, onde ainda nao ha historico suficiente. Manter o mesmo tamanho
    evita o erro classico de desalinhar a media do preco por alguns dias.
    """
    if janela < 1:
        raise ValueError("janela precisa ser pelo menos 1")
    saida: list[float | None] = []
    soma = 0.0
    for posicao, valor in enumerate(valores):
        soma += valor
        if posicao >= janela:
            soma -= valores[posicao - janela]
        saida.append(soma / janela if posicao >= janela - 1 else None)
    return saida


def distancia_da_media(valores: list[float], janela: int) -> list[float]:
    """Quanto cada ponto esta acima ou abaixo da sua media movel, em fracao.

    E isto que o termometro compara: nao o preco, que nao diz nada sozinho,
    mas o quanto ele esta esticado em relacao a propria media.
    """
    medias = media_movel(valores, janela)
    return [
        valor / media - 1
        for valor, media in zip(valores, medias)
        if media not in (None, 0)
    ]


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
