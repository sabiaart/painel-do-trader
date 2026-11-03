"""Termometro do mercado: medo e ganancia, de 0 a 100.

Como a nota sai
---------------
Cada componente vira um PERCENTIL dos ultimos 252 pregoes. Isto e, a
pergunta nao e "o dolar esta alto?" - e "em quantos por cento dos ultimos
252 pregoes o dolar esteve mais barato do que hoje?".

Percentil e o que torna componentes de unidades diferentes comparaveis:
pontos de indice, por cento ao ano e bilhoes de reais viram todos uma nota
de 0 a 100. A nota final e a media simples das notas disponiveis.

Componentes que sobem quando ha MEDO sao invertidos (volatilidade e dolar),
para que 0 seja sempre medo e 100 sempre ganancia.

O que nao tem fonte, e por que fica de fora
-------------------------------------------
A especificacao pede 7 componentes. Quatro tem fonte publica hoje:

  momento, volatilidade, fluxo estrangeiro e dolar.

Tres nao tem, e entram no arquivo marcados como indisponiveis, com o motivo:

  - Amplitude (% das acoes acima da media de 200 dias): precisaria do
    historico das ~85 acoes do Ibovespa. A Alpha Vantage gratuita da 25
    consultas por DIA.
  - Posicao do estrangeiro no WIN: a B3 nao publica a divisao de posicoes
    por tipo de participante.
  - Protecao (put/call de BOVA11): sem fonte gratuita.

Eles NAO entram na media. Um componente faltando vale menos do que um
componente chutado: a media de quatro notas reais e um numero honesto, a
media de quatro reais e tres inventadas nao e nada.

Sobre o Ibovespa
----------------
O momento usa o EWZ, o ETF de Brasil negociado em Nova York, como
substituto do Ibovespa - a mesma troca que o placar ja faz, e pela mesma
razao: o indice em si exige dado licenciado. Nao e a mesma coisa (o EWZ tem
dolar dentro), e a tela diz isso.
"""

from __future__ import annotations

import calculos
import comum
import fontes

JANELA_PERCENTIL = 252  # um ano de pregoes, quando a fonte alcanca

# A especificacao pedia media de 125 pregoes para o momento. A Alpha
# Vantage gratuita entrega 100 pregoes (o historico longo virou pago), e
# uma media de 125 sobre 100 dias nao existe. Com media de 50 sobram 50
# pontos para o percentil: pouco, e a tela avisa.
MEDIA_MOMENTO = 50
MEDIA_VOLATILIDADE = 50
MEDIA_DOLAR = 125
JANELA_FLUXO = 5  # pregoes somados no componente de fluxo


def _nota(serie: list[float], *, inverte: bool) -> int:
    """Percentil do ultimo valor da serie, de 0 a 100.

    `inverte` para os componentes em que subir significa medo.

    Uma propriedade que surpreende e nao e defeito: numa alta perfeitamente
    constante, a distancia para a media se estabiliza, e o percentil dela
    fica baixo. Isto aqui mede ESTICAMENTO, nao tendencia - "o preco esta
    longe da propria media?", nao "o preco esta subindo?". E o que a
    especificacao pediu, e e o que o indice de medo e ganancia da CNN faz.
    """
    if len(serie) < 2:
        raise ValueError("série curta demais para percentil")
    historico = serie[-JANELA_PERCENTIL:]
    nota = calculos.percentil(historico[-1], historico)
    return 100 - nota if inverte else nota


def _momento(chave: str) -> dict:
    """Preco contra a media movel. Esticado para cima = ganancia."""
    import time

    # O termometro roda logo depois do placar, que ja gastou dez consultas
    # seguidas. Sem esta pausa a Alpha Vantage responde "spread out your
    # requests" em vez de dados, e o componente cai por nada.
    time.sleep(2)
    serie = fontes.alpha_serie("EWZ", chave)
    distancias = calculos.distancia_da_media([v for _, v in serie], MEDIA_MOMENTO)
    return {
        "nome": "Momento (EWZ)",
        "nota": _nota(distancias, inverte=False),
        "fonte": "Alpha Vantage (EWZ, no lugar do Ibovespa)",
        "detalhe": f"preço contra a média de {MEDIA_MOMENTO} pregões",
        "janela": min(len(distancias), JANELA_PERCENTIL),
        "substitui": "Ibovespa",
        "curto": True,
    }


def _volatilidade() -> dict:
    """Volatilidade implicita contra a media de 50 dias. Alta = medo."""
    serie = fontes.vol_ewz()
    distancias = calculos.distancia_da_media([v for _, v in serie], MEDIA_VOLATILIDADE)
    return {
        "nome": "Volatilidade (VXEWZ)",
        "nota": _nota(distancias, inverte=True),
        "fonte": "FRED / Cboe (VXEWZCLS)",
        "detalhe": f"contra a média de {MEDIA_VOLATILIDADE} pregões; volatilidade alta é medo",
        "janela": min(len(distancias), JANELA_PERCENTIL),
        "substitui": "VIX do Ibovespa",
        "citacao": (
            "Chicago Board Options Exchange, CBOE Brazil ETF Volatility Index "
            "[VXEWZCLS], retrieved from FRED, Federal Reserve Bank of St. Louis."
        ),
    }


def _dolar() -> dict:
    """Dolar contra a media de 125 dias. Dolar subindo = procura por
    porto seguro = medo."""
    serie = fontes.dolar_ptax()
    distancias = calculos.distancia_da_media([v for _, v in serie], MEDIA_DOLAR)
    return {
        "nome": "Porto seguro (dólar)",
        "nota": _nota(distancias, inverte=True),
        "fonte": "Banco Central (SGS 1, dólar PTAX de venda)",
        "detalhe": f"contra a média de {MEDIA_DOLAR} pregões; dólar subindo é medo",
        "janela": min(len(distancias), JANELA_PERCENTIL),
    }


def _fluxo() -> dict:
    """Soma do fluxo estrangeiro dos ultimos 5 pregoes.

    Este e o componente mais fraco dos quatro, e a tela precisa dizer: a B3
    so publica cerca de 21 pregoes, entao o percentil e calculado sobre
    pouco mais de uma dezena de janelas, nao sobre um ano. Serve para dizer
    se o fluxo recente e forte ou fraco PARA O PERIODO QUE TEMOS, nao para
    a historia.
    """
    import b3

    serie = b3.fluxo_estrangeiro_diario()
    valores = [v for _, v in serie]
    if len(valores) <= JANELA_FLUXO:
        raise comum.FonteIndisponivel(
            f"fluxo: {len(valores)} pregões, preciso de mais de {JANELA_FLUXO}"
        )
    somas = [
        sum(valores[i : i + JANELA_FLUXO])
        for i in range(len(valores) - JANELA_FLUXO + 1)
    ]
    return {
        "nome": f"Fluxo estrangeiro {JANELA_FLUXO}d",
        "nota": _nota(somas, inverte=False),
        "fonte": "B3, Boletim Diário (participação dos investidores)",
        "detalhe": f"soma de {JANELA_FLUXO} pregões, comparada com as outras janelas do período",
        "janela": len(somas),
        "curto": True,
    }


# Os que a especificacao pede e nao tem de onde vir.
SEM_FONTE = [
    {
        "nome": "Amplitude das ações",
        "nota": None,
        "motivo": "exigiria o histórico das ~85 ações do Ibovespa; a cota gratuita é de 25 consultas por dia",
        "permanente": True,
    },
    {
        "nome": "Posição estrangeiro no WIN",
        "nota": None,
        "motivo": "a B3 não publica posições por tipo de participante",
        "permanente": True,
    },
    {
        "nome": "Proteção (put/call)",
        "nota": None,
        "motivo": "sem fonte gratuita para as opções de BOVA11",
        "permanente": True,
    },
]

ZONAS = [
    (25, "Medo extremo"),
    (45, "Medo"),
    (56, "Neutro"),
    (76, "Ganância"),
    (101, "Ganância extrema"),
]


def zona(nota: int) -> str:
    for limite, nome in ZONAS:
        if nota < limite:
            return nome
    return ZONAS[-1][1]


def calcular() -> tuple[dict, list[str]]:
    """Monta o termometro. Devolve (dados, falhas)."""
    chave = comum.chave("ALPHA_VANTAGE")

    componentes: list[dict] = []
    falhas: list[str] = []

    tarefas = [
        ("Momento (EWZ)", (lambda: _momento(chave)) if chave else None),
        ("Volatilidade (VXEWZ)", _volatilidade),
        ("Porto seguro (dólar)", _dolar),
        (f"Fluxo estrangeiro {JANELA_FLUXO}d", _fluxo),
    ]

    for rotulo, funcao in tarefas:
        if funcao is None:
            componentes.append(
                {"nome": rotulo, "nota": None, "motivo": "falta a chave ALPHA_VANTAGE"}
            )
            falhas.append(f"{rotulo}: falta a chave ALPHA_VANTAGE")
            continue
        try:
            componentes.append(funcao())
        except (comum.FonteIndisponivel, ValueError, IndexError) as erro:
            # O componente continua na lista, sem nota e com o motivo. Sumir
            # da tela faria a nota parecer mais completa do que e.
            componentes.append({"nome": rotulo, "nota": None, "motivo": str(erro)[:200]})
            falhas.append(f"{rotulo}: {erro}")

    com_nota = [c for c in componentes if c["nota"] is not None]
    if not com_nota:
        raise comum.FonteIndisponivel("; ".join(falhas) or "nenhum componente respondeu")

    nota = round(sum(c["nota"] for c in com_nota) / len(com_nota))

    dados = comum.cabecalho("Alpha Vantage, FRED/Cboe, Banco Central e B3")
    dados["nota"] = nota
    dados["zona"] = zona(nota)
    dados["componentes"] = componentes + SEM_FONTE
    dados["usados"] = len(com_nota)
    # Sempre 7: e o que a especificacao pede. Se encolhesse junto com as
    # falhas do dia, "3 de 3" leria como termometro completo.
    dados["previstos"] = len(tarefas) + len(SEM_FONTE)

    # "Ontem", "semana" e "mes" so existem se alguem tiver anotado a nota
    # naqueles dias. Ninguem recalcula o termometro do passado: as fontes
    # de hoje nao contam como o fluxo estava ha um mes. Entao o painel
    # guarda a nota de cada dia aqui, e ate ter historico mostra travessao.
    historico = _historico()
    historico[comum.agora()[:10]] = nota
    dados["historico"] = historico
    dados["ontem"] = _nota_de(historico, 1)
    dados["semana"] = _nota_de(historico, 7)
    dados["mes"] = _nota_de(historico, 30)
    dados["falhas"] = falhas
    return dados, falhas


def _historico() -> dict[str, int]:
    anterior = comum.ler("termometro") or {}
    bruto = anterior.get("historico")
    if not isinstance(bruto, dict):
        return {}
    return {d: n for d, n in bruto.items() if isinstance(n, int)}


def _nota_de(historico: dict[str, int], dias_atras: int) -> int | None:
    """Nota de ha N dias, ou a mais proxima ANTES disso.

    Aceita a mais proxima anterior porque o painel nao roda todo dia:
    fim de semana, feriado, computador desligado. O que nao vale e pegar
    uma nota depois da data pedida, que seria comparar com o futuro.
    """
    from datetime import date, timedelta

    alvo = date.today() - timedelta(days=dias_atras)
    candidatas = []
    for dia, nota in historico.items():
        try:
            quando = date.fromisoformat(dia)
        except ValueError:
            continue
        if quando <= alvo:
            candidatas.append((quando, nota))
    if not candidatas:
        return None
    return max(candidatas)[1]
