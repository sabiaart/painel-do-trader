"""Opcoes: posicoes em aberto por strike, da B3.

Para incluir outro ativo
------------------------
Acrescente uma linha em ATIVOS, abaixo. O `codigo` e o que a B3 escreve na
coluna "Ativo" das opcoes - normalmente as quatro primeiras letras do
papel ("BOVA" para BOVA11, "PETR" para PETR4). O resto se vira sozinho.

Hoje o painel mostra um ativo de cada vez (o primeiro da lista), porque a
pagina de opcoes tem um bloco so. A coleta ja traz todos.

De onde vem cada numero
-----------------------
Tudo do Boletim Diario da B3, tres tabelas que se completam:

  Posicoes em aberto       quantas opcoes de cada serie estao abertas
  Cadastro de instrumentos o strike e o vencimento de cada serie
  Negocios consolidados    o fechamento do ativo e de cada opcao

A primeira sozinha nao serve: ela diz que a serie BOVAK240W2 tem 1.101
contratos, mas nao diz que strike e esse. O cadastro e quem conta.

Uma pegadinha que custou caro
-----------------------------
Na tabela de posicoes em aberto, a coluna "Contratos em aberto" vem VAZIA
para opcao - o numero esta em "Total de posicoes". Ler a coluna de nome
obvio daria uma tabela inteira de zeros, sem erro nenhum na tela.
"""

from __future__ import annotations

from datetime import date, datetime

import b3
import comum

# Para incluir outro ativo, acrescente aqui. So isto.
ATIVOS = [
    {"codigo": "BOVA", "nome": "BOVA11", "descricao": "ETF que segue o Ibovespa"},
]

# Quantos strikes mostrar de cada lado do preco. A cauda tem muito strike
# com posicao irrelevante, que so suja o grafico.
STRIKES_POR_LADO = 8

SELIC_SGS = 432  # meta Selic definida pelo Copom, em % ao ano


DIAS_A_FRENTE = 60  # ate onde procurar o vencimento que manda


def posicoes_por_vencimento(series: dict, hoje: date) -> dict[str, int]:
    """Total de contratos em aberto em cada vencimento futuro."""
    totais: dict[str, int] = {}
    for dados in series.values():
        venc = dados.get("vencimento")
        if not venc:
            continue
        try:
            quando = date.fromisoformat(venc)
        except ValueError:
            continue
        if quando < hoje:
            continue
        totais[venc] = totais.get(venc, 0) + dados.get("posicoes", 0)
    return totais


def _vencimento_principal(series: dict, hoje: date) -> str | None:
    """O vencimento que concentra posicao, nao o mais proximo.

    Isto importa muito e foi medido: em 02/11/2026, o semanal de 06/11
    tinha 4,9 milhoes de contratos e o mensal de 19/11 tinha 137 milhoes -
    vinte e oito vezes mais. Pegar o mais proximo so porque e o proximo
    mostraria o gamma do lugar errado.

    Entre os vencimentos dos proximos DIAS_A_FRENTE dias, fica com o de
    maior posicao em aberto.
    """
    from datetime import timedelta

    totais = posicoes_por_vencimento(series, hoje)
    limite = (hoje + timedelta(days=DIAS_A_FRENTE)).isoformat()
    perto = {v: t for v, t in totais.items() if v <= limite}
    candidatos = perto or totais
    if not candidatos:
        return None
    return max(candidatos, key=lambda v: candidatos[v])


def _juros() -> tuple[float, str]:
    """Selic ao ano, em fracao. Se o Banco Central nao responder, usa um
    valor fixo e diz que usou - o juro mexe pouco no resultado, mas
    inventar sem avisar nao."""
    import fontes

    try:
        serie = fontes.bcb_serie(SELIC_SGS, dias=120)
        return serie[-1][1] / 100, f"Banco Central (SGS {SELIC_SGS}, meta Selic)"
    except (comum.FonteIndisponivel, ValueError, IndexError):
        return 0.1075, "valor fixo: o Banco Central não respondeu"


def _volatilidade() -> tuple[float, str]:
    """Volatilidade para o calculo de gamma.

    Esta e a parte fraca, e precisa estar escrito: usamos UMA volatilidade
    para todos os strikes, tirada do VXEWZ. O certo seria a volatilidade
    implicita de cada serie, calculada a partir do premio dela. O premio
    esta no boletim; falta implementar o calculo.

    Uma volatilidade so achata o sorriso de volatilidade, entao o gamma das
    pontas sai subestimado.
    """
    import fontes

    try:
        serie = fontes.vol_ewz()
        return serie[-1][1] / 100, f"VXEWZ de {serie[-1][0]:%d/%m}"
    except (comum.FonteIndisponivel, ValueError, IndexError):
        return 0.25, "valor fixo: o FRED não respondeu"


def coletar(dia: date | None = None) -> dict:
    """Monta o arquivo de opcoes do primeiro ativo de ATIVOS."""
    pregoes = b3.dias_uteis()
    dia = dia or pregoes[0]
    hoje = date.today()

    codigos = {a["codigo"] for a in ATIVOS}
    abertas = b3.posicoes_em_aberto_opcoes(dia, codigos)
    cadastro = b3.cadastro_opcoes(dia, set(abertas))

    # Junta posicao com strike. Serie sem cadastro fica de fora: sem strike
    # ela nao tem onde ser desenhada.
    series: dict[str, dict] = {}
    sem_cadastro = 0
    posicoes_sem_cadastro = 0
    for papel, posicao in abertas.items():
        ficha = cadastro.get(papel)
        if not ficha:
            # Acontece de valer muito: ja vimos uma serie com 10 milhoes de
            # contratos em aberto que o cadastro do mesmo dia nao listava.
            # Sem strike nao da para desenhar, mas o tamanho do buraco
            # precisa aparecer na tela em vez de sumir.
            sem_cadastro += 1
            posicoes_sem_cadastro += posicao.get("posicoes", 0)
            continue
        series[papel] = {**posicao, **ficha}

    if not series:
        raise comum.FonteIndisponivel("nenhuma série de opção com strike conhecido")

    alvo = ATIVOS[0]
    do_ativo = {p: d for p, d in series.items() if d["ativo"] == alvo["codigo"]}
    if not do_ativo:
        raise comum.FonteIndisponivel(f"nenhuma opção de {alvo['nome']} em aberto")

    vencimento = _vencimento_principal(do_ativo, hoje)
    if not vencimento:
        raise comum.FonteIndisponivel(f"{alvo['nome']}: nenhum vencimento em aberto")
    do_vencimento = {p: d for p, d in do_ativo.items() if d["vencimento"] == vencimento}

    # Preco do ativo, do mesmo pregao das posicoes. Pelo IOPV, que e uma
    # pagina so; a tabela de negocios consolidados nao traz ETF, e custaria
    # 74 paginas para descobrir isso.
    preco = b3.valor_de_etf(dia, alvo["codigo"])
    fonte_preco = "IOPV da B3 (valor de referência da cesta do ETF)"

    # Agrupa por strike, somando call e put.
    por_strike: dict[float, dict] = {}
    for dados in do_vencimento.values():
        linha = por_strike.setdefault(dados["strike"], {"call_oi": 0, "put_oi": 0})
        linha["call_oi" if dados["tipo"] == "call" else "put_oi"] += dados["posicoes"]

    # Mantem os strikes em volta do preco: a cauda e ruido no grafico.
    ordenados = sorted(por_strike)
    perto = min(range(len(ordenados)), key=lambda i: abs(ordenados[i] - preco))
    recorte = ordenados[max(0, perto - STRIKES_POR_LADO) : perto + STRIKES_POR_LADO + 1]

    vencimento_data = date.fromisoformat(vencimento)
    prazo_dias = max((vencimento_data - hoje).days, 1)

    vol, fonte_vol = _volatilidade()
    juros, fonte_juros = _juros()

    dados = comum.cabecalho("B3, Boletim Diário (posições em aberto e cadastro)")
    dados["ativo"] = alvo["nome"]
    dados["ativo_descricao"] = alvo["descricao"]
    dados["vencimento"] = f"{vencimento_data:%d/%m}"
    dados["vencimento_iso"] = vencimento
    dados["referencia"] = f"fechamento de {dia:%d/%m}"
    dados["pregao"] = dia.isoformat()
    dados["preco"] = round(preco, 2)
    dados["preco_fonte"] = fonte_preco
    dados["prazo_anos"] = round(prazo_dias / 365, 5)
    dados["prazo_dias"] = prazo_dias
    dados["vol_implicita"] = round(vol, 4)
    dados["vol_fonte"] = fonte_vol
    dados["juros"] = round(juros, 4)
    dados["juros_fonte"] = fonte_juros
    # A conversao para pontos do Ibovespa exigiria o nivel do indice, que
    # nao temos de fonte livre. Nulo faz a pagina esconder a linha, em vez
    # de multiplicar por um numero inventado.
    dados["razao_ibov"] = None
    dados["unidade_oi"] = "contratos"
    dados["strikes"] = [
        {
            "strike": round(s, 2),
            "call_oi": por_strike[s]["call_oi"],
            "put_oi": por_strike[s]["put_oi"],
        }
        for s in recorte
    ]
    dados["series_no_vencimento"] = len(do_vencimento)
    dados["series_sem_cadastro"] = sem_cadastro
    dados["posicoes_sem_cadastro"] = posicoes_sem_cadastro
    cobertas = sum(d["posicoes"] for d in series.values())
    total_posicoes = cobertas + posicoes_sem_cadastro
    dados["cobertura_pct"] = (
        round(cobertas / total_posicoes * 100, 1) if total_posicoes else None
    )
    # Todos os vencimentos com posicao, para dar para conferir que o
    # escolhido e mesmo o maior - e para um dia a pagina poder trocar.
    totais = posicoes_por_vencimento(do_ativo, hoje)
    dados["vencimentos_disponiveis"] = [
        {"vencimento": v, "posicoes": totais[v]} for v in sorted(totais)
    ]
    return dados
