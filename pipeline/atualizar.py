"""Roda o pipeline inteiro. E isto que o robo das 7h executa.

    python pipeline/atualizar.py

Cada fonte e tratada em separado. Se uma cair, as outras seguem e o arquivo
da que caiu fica como estava, marcado como desatualizado. O programa so
termina com erro se TODAS as fontes falharem - nesse caso vale avisar.
"""

from __future__ import annotations

import sys
import time
from datetime import date

import b3
import calculos
import comum
import fontes
import historico
import indicadores
import resumo as monta_resumo
import opcoes as coletar_opcoes
import termometro as calc_termometro

JANELA_VOL = 21  # pregoes usados na volatilidade historica
PAUSA_ENTRE_CONSULTAS = 1.5  # segundos; a Alpha Vantage aceita 1 por segundo


def _niveis_do_contrato(ativo: str, cotacao: dict) -> dict:
    """Monta o painel de um futuro a partir do contrato de verdade."""
    simbolo = cotacao["symbol"]
    serie = fontes.futuro_historico(simbolo)

    ajustes = [d["ajuste"] for d in serie]
    vol = calculos.volatilidade_historica(ajustes, JANELA_VOL)
    ajuste = float(cotacao["settlement"])
    desvio = calculos.movimento_esperado(ajuste, vol)

    acertos, avaliados = calculos.faixa_respeitada(serie, janela=30, vol_janela=JANELA_VOL)
    vencimento = date.fromisoformat(cotacao["expirationDate"])
    casas = 0 if ativo == "WIN" else 1

    return {
        "nome": f"{ativo} · {cotacao.get('assetDescription', ativo)}",
        "contrato": simbolo,
        "ajuste": round(ajuste, casas),
        # Gap previsto precisa de preco de pre-mercado, que nao temos.
        "gap": None,
        "maxima": round(float(cotacao["high"]), casas) if cotacao.get("high") else None,
        "minima": round(float(cotacao["low"]), casas) if cotacao.get("low") else None,
        "desvio": round(desvio, casas),
        "casas": casas,
        "dias_vencimento": (vencimento - date.today()).days,
        "vencimento": vencimento.isoformat(),
        "exemplo_preco": f"{ajuste:,.{casas}f}".replace(",", "@").replace(".", ",").replace("@", "."),
        "faixa_ampliada": None,
        "acertos": acertos if avaliados else None,
        "janela": avaliados or None,
        "fechamento": None,
        "pregao": serie[-1]["data"].isoformat(),
        "volatilidade": {
            "anual_pct": round(vol * 100, 1),
            "metodo": f"histórica de {JANELA_VOL} pregões do próprio contrato",
            "fonte": f"brapi.dev ({simbolo}, preço de ajuste da B3)",
            "citacao": None,
            "data": serie[-1]["data"].isoformat(),
        },
    }


def atualizar_niveis() -> dict:
    """Niveis do dia de WIN e WDO, com o contrato em vigor.

    Fonte principal: brapi, que da ajuste, maxima, minima e o historico do
    proprio contrato. Se ela cair, cai para o plano antigo: mantem o ajuste
    de exemplo e tira a volatilidade do Banco Central e do FRED.
    """
    atual = comum.ler("niveis")
    if atual is None:
        raise comum.FonteIndisponivel("site/data/niveis.json sumiu")

    for campo in ("metodo_volatilidade", "motivo_falha", "verificado_em"):
        atual.pop(campo, None)

    resultados: dict[str, str] = {}
    falhas: list[str] = []
    reais = 0

    try:
        vigentes = fontes.futuros_vigentes()
    except comum.FonteIndisponivel as erro:
        vigentes = {}
        falhas.append(f"brapi: {erro}")

    for ativo, chave in (("WIN", "win"), ("WDO", "wdo")):
        if ativo not in vigentes:
            continue
        try:
            atual["ativos"][chave] = _niveis_do_contrato(ativo, vigentes[ativo])
            reais += 1
            d = atual["ativos"][chave]
            acerto = f", faixa respeitada em {d['acertos']}/{d['janela']}" if d["acertos"] is not None else ""
            resultados[chave] = f"{d['contrato']} ajuste {d['ajuste']}, vol {d['volatilidade']['anual_pct']}%{acerto}"
        except (comum.FonteIndisponivel, ValueError, KeyError) as erro:
            falhas.append(f"{ativo}: {erro}")

    # --- Plano B, so para quem nao veio da brapi ---
    if "win" not in resultados or "wdo" not in resultados:
        _volatilidade_de_reserva(atual, resultados, falhas)

    if not resultados:
        raise comum.FonteIndisponivel("; ".join(falhas) or "nenhuma fonte respondeu")

    tudo_real = reais == 2
    atual.update(
        comum.cabecalho(
            "brapi.dev (ajuste e histórico da B3)" if tudo_real
            else "brapi.dev, Banco Central e FRED; parte ainda de exemplo",
            exemplo=not tudo_real,
        )
    )
    atual["falhas"] = falhas
    comum.gravar("niveis", atual)
    return resultados


def _volatilidade_de_reserva(atual: dict, resultados: dict, falhas: list) -> None:
    """Plano B: ajuste continua de exemplo, volatilidade vem do BCB e do FRED."""
    if "wdo" not in resultados:
        try:
            serie = fontes.dolar_ptax()
            precos = [v for _, v in serie]
            vol = calculos.volatilidade_historica(precos, JANELA_VOL)
            alvo = atual["ativos"]["wdo"]
            alvo["desvio"] = round(calculos.movimento_esperado(precos[-1] * 1000, vol), 1)
            alvo["acertos"] = None
            alvo["volatilidade"] = {
                "anual_pct": round(vol * 100, 1),
                "metodo": f"histórica de {JANELA_VOL} pregões",
                "fonte": "Banco Central (SGS 1, dólar PTAX de venda)",
                "citacao": "Banco Central do Brasil, sistema SGS, série 1 (dólar PTAX de venda).",
                "data": serie[-1][0].isoformat(),
            }
            resultados["wdo"] = f"reserva: vol {vol * 100:.1f}% (PTAX)"
        except (comum.FonteIndisponivel, ValueError) as erro:
            falhas.append(f"dólar PTAX: {erro}")

    if "win" not in resultados:
        try:
            serie = fontes.vol_ewz()
            vol = serie[-1][1] / 100
            alvo = atual["ativos"]["win"]
            alvo["desvio"] = round(calculos.movimento_esperado(alvo["ajuste"], vol))
            alvo["acertos"] = None
            alvo["volatilidade"] = {
                "anual_pct": round(vol * 100, 1),
                "metodo": "implícita do EWZ (reserva)",
                "fonte": "FRED / Cboe (VXEWZCLS)",
                "citacao": (
                    "Chicago Board Options Exchange, CBOE Brazil ETF Volatility Index "
                    "[VXEWZCLS], retrieved from FRED, Federal Reserve Bank of St. Louis."
                ),
                "data": serie[-1][0].isoformat(),
            }
            resultados["win"] = f"reserva: vol {vol * 100:.1f}% (VXEWZ)"
        except (comum.FonteIndisponivel, ValueError, IndexError) as erro:
            falhas.append(f"VXEWZ: {erro}")


def atualizar_globais() -> str:
    """Placar dos indicadores e grade "O que mexe hoje".

    Os dois saem da mesma busca, para nao gastar o dobro das consultas:
    o plano gratuito da Alpha Vantage e de 25 por dia e o placar usa 10.
    """
    chave = comum.chave("ALPHA_VANTAGE")
    if not chave:
        raise fontes.SemChave(
            "falta a chave ALPHA_VANTAGE. Crie uma conta gratuita em "
            "alphavantage.co e coloque a chave em chaves.env"
        )

    coletados = []
    falhas = []
    for posicao, (simbolo, nome, peso, inverte, substitui) in enumerate(indicadores.INDICADORES):
        # A Alpha Vantage aceita 1 consulta por segundo. Sem esta pausa ela
        # responde com um aviso em vez de dados, e o placar vem vazio.
        if posicao:
            time.sleep(PAUSA_ENTRE_CONSULTAS)
        try:
            c = fontes.alpha_cotacao(simbolo, chave)
        except comum.FonteIndisponivel as erro:
            falhas.append(str(erro))
            continue
        coletados.append(
            {
                "nome": nome,
                "valor": f"{c['preco']:,.2f}".replace(",", "@").replace(".", ",").replace("@", "."),
                "variacao": round(c["variacao"], 2),
                "unidade": "%",
                "peso": peso,
                "favoravel": indicadores.favoravel(c["variacao"], inverte),
                "inverte": inverte,
                "substitui": substitui,
                "data": c["data"].isoformat(),
            }
        )

    # Metade dos indicadores faltando ja nao e um placar: e um palpite.
    if len(coletados) < len(indicadores.INDICADORES) / 2:
        raise comum.FonteIndisponivel(
            f"só {len(coletados)} de {len(indicadores.INDICADORES)} indicadores vieram. "
            + ("; ".join(falhas[:2]) if falhas else "")
        )

    origem = "Alpha Vantage (fechamento do pregão anterior)"
    pregao = max(i["data"] for i in coletados)

    grade = comum.cabecalho(origem)
    grade["ativos"] = coletados
    grade["pregao"] = pregao
    grade["falhas"] = falhas
    comum.gravar("globais", grade)

    favoraveis = sum(1 for i in coletados if i["favoravel"])
    placar = comum.cabecalho(origem)
    placar["favoraveis"] = favoraveis
    placar["total"] = len(coletados)
    placar["pregao"] = pregao
    placar["indicadores"] = [
        {"nome": i["nome"], "favoravel": i["favoravel"]} for i in coletados
    ]
    comum.gravar("placar", placar)

    aviso = f" ({len(falhas)} falharam)" if falhas else ""
    return f"{favoraveis} de {len(coletados)} a favor, pregão de {pregao}{aviso}"


def atualizar_fluxo() -> str:
    """Bloco "Fluxo estrangeiro", direto do Boletim Diario da B3.

    Leia o aviso no topo de b3.py antes de mexer: esta coleta e automatizada
    e os termos da B3 a proibem. Foi uma decisao do dono do projeto, para
    uso pessoal e sem republicacao.
    """
    serie = b3.fluxo_estrangeiro_diario()
    ultimos = serie[-20:]
    valores = [round(v, 3) for _, v in ultimos]
    fim = ultimos[-1][0]

    # "Mes" e o mes do ultimo pregao que temos (outubro, mesmo em novembro),
    # porque o dado chega com dois dias de atraso e na virada ainda nao ha
    # nada do mes corrente. O rotulo na tela diz qual mes e.
    do_mes = sum(v for d, v in serie if (d.year, d.month) == (fim.year, fim.month))

    dados = comum.cabecalho("B3, Boletim Diário (participação dos investidores)")
    dados["unidade"] = "R$ bi"
    dados["pregoes"] = valores
    # As datas de cada barra. A tela nao usa, mas o historico usa: sem
    # elas, os 19 pregoes entrariam na memoria sem saber de que dia sao.
    dados["datas"] = [d.isoformat() for d, _ in ultimos]
    dados["ontem"] = valores[-1]
    dados["mes"] = round(do_mes, 2)
    dados["mes_nome"] = MESES[fim.month - 1]
    # So temos a janela que a B3 publica (cerca de 21 pregoes). Somar "ano"
    # com isso daria um numero que parece do ano e nao e.
    dados["ano"] = None
    dados["pregao"] = fim.isoformat()
    dados["pregoes_no_historico"] = len(serie)
    dados["parcial"] = False
    comum.gravar("fluxo", dados)

    return f"{len(ultimos)} pregões até {fim:%d/%m}, último {valores[-1]:+.2f} R$ bi"


#  Os quatro contratos que interessam a quem opera WIN e WDO: o mini e o
#  cheio de cada um. O cheio entra porque e nele que o institucional
#  costuma estar, e o tamanho dele contextualiza o mini.
CONTRATOS = [
    ("WIN", "WIN · mini índice"),
    ("IND", "IND · índice cheio"),
    ("WDO", "WDO · mini dólar"),
    ("DOL", "DOL · dólar cheio"),
]

JANELA_CONTRATOS = 5  # pregoes para a variacao


def atualizar_contratos() -> str:
    """Bloco "Contratos em aberto", do quadro analítico da B3.

    Substitui o antigo "Quem esta comprado no WIN". A divisao por tipo de
    participante nao e publica; o que existe e o total por contrato. E outra
    pergunta - quanto esta em jogo, nao quem esta de que lado - e a tela
    precisa dizer isso.
    """
    serie = b3.contratos_em_aberto_serie()
    quando, atuais = serie[-1]

    # Cinco pregoes atras. Com menos historico, compara com o mais antigo
    # que houver e a tela avisa quantos pregoes sao.
    passados = serie[-(JANELA_CONTRATOS + 1)][1] if len(serie) > JANELA_CONTRATOS else (
        serie[0][1] if len(serie) > 1 else {}
    )
    janela = min(JANELA_CONTRATOS, len(serie) - 1)

    lista = []
    for sigla, rotulo in CONTRATOS:
        atual = atuais.get(sigla)
        if not atual:
            continue
        antes = (passados.get(sigla) or {}).get("contratos")
        agora = atual["contratos"]
        variacao = None if antes in (None, 0) else (agora / antes - 1) * 100
        lista.append(
            {
                "nome": rotulo,
                "contratos": agora,
                "variacao": None if variacao is None else round(variacao, 1),
                "direcao": None if variacao is None else ("sobe" if variacao >= 0 else "desce"),
            }
        )

    if not lista:
        raise comum.FonteIndisponivel("nenhum dos contratos do painel apareceu no quadro")

    dados = comum.cabecalho("B3, Boletim Diário (quadro analítico das posições em aberto)")
    dados["contratos"] = lista
    dados["pregao"] = quando.isoformat()
    dados["janela"] = janela
    dados["pregoes_no_historico"] = len(serie)
    comum.gravar("contratos", dados)

    win = next((c for c in lista if c["nome"].startswith("WIN")), lista[0])
    return f"{len(lista)} contratos, pregão {quando:%d/%m}, WIN com {win['contratos']:,} em aberto".replace(",", ".")


MESES = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


def atualizar_fontes(estado: dict[str, dict]) -> None:
    """Grava o estado de cada fonte, para a pagina /sobre mostrar."""
    dados = comum.cabecalho("pipeline", exemplo=False)
    dados["fontes"] = estado
    comum.gravar("fontes", dados)


def main() -> int:
    print(f"Pipeline do Painel do Trader - {comum.agora()}")
    estado: dict[str, dict] = {}
    houve_sucesso = False

    print("\n[niveis] volatilidade de WIN e WDO")
    try:
        resultados = atualizar_niveis()
        houve_sucesso = True
        for ativo, resumo in resultados.items():
            print(f"  ok {ativo}: {resumo}")
        estado["niveis"] = {
            "situacao": "ok" if len(resultados) == 2 else "parcial",
            "detalhe": " · ".join(resultados.values()),
            "em": comum.agora(),
        }
    except comum.FonteIndisponivel as erro:
        comum.manter_anterior("niveis", str(erro))
        estado["niveis"] = {"situacao": "falhou", "detalhe": str(erro), "em": comum.agora()}

    print("\n[globais] placar e grade de mercados")
    try:
        resumo = atualizar_globais()
        houve_sucesso = True
        print(f"  ok {resumo}")
        estado["globais"] = {"situacao": "ok", "detalhe": resumo, "em": comum.agora()}
    except fontes.SemChave as erro:
        # Falta de chave nao e fonte fora do ar: nada a preservar, nada a
        # marcar como desatualizado. So avisa e segue.
        print(f"  - pulado: {erro}")
        estado["globais"] = {"situacao": "sem chave", "detalhe": str(erro), "em": comum.agora()}
    except comum.FonteIndisponivel as erro:
        comum.manter_anterior("globais", str(erro))
        comum.manter_anterior("placar", str(erro))
        estado["globais"] = {"situacao": "falhou", "detalhe": str(erro), "em": comum.agora()}

    # --- Blocos que vem de arquivo baixado a mao ---
    #
    # O robo NUNCA acessa b3.com.br: a B3 proibe coleta automatizada. Ele le
    # o que estiver em b3-manual/. Pasta vazia nao e falha: e so nao ter
    # arquivo novo hoje, e o dado de ontem continua valendo.
    print("\n[fluxo] fluxo estrangeiro (Boletim Diário da B3)")
    try:
        resumo = atualizar_fluxo()
        houve_sucesso = True
        print(f"  ok {resumo}")
        estado["fluxo"] = {"situacao": "ok", "detalhe": resumo, "em": comum.agora()}
    except comum.FonteIndisponivel as erro:
        comum.manter_anterior("fluxo", str(erro))
        estado["fluxo"] = {"situacao": "falhou", "detalhe": str(erro), "em": comum.agora()}

    print("\n[termometro] medo e ganância")
    try:
        dados, falhas_term = calc_termometro.calcular()
        houve_sucesso = True
        comum.gravar("termometro", dados)
        resumo = (
            f"nota {dados['nota']} ({dados['zona']}), "
            f"{dados['usados']} de {dados['previstos']} componentes"
        )
        print(f"  ok {resumo}")
        for falha in falhas_term:
            print(f"    - {falha[:120]}")
        estado["termometro"] = {
            "situacao": "parcial" if falhas_term else "ok",
            "detalhe": resumo,
            "em": comum.agora(),
        }
    except comum.FonteIndisponivel as erro:
        comum.manter_anterior("termometro", str(erro))
        estado["termometro"] = {"situacao": "falhou", "detalhe": str(erro), "em": comum.agora()}

    # Depois dos globais, do fluxo e do termometro: o resumo le os tres.
    print("\n[resumo] resumo do dia")
    try:
        dados = monta_resumo.montar()
        houve_sucesso = True
        comum.gravar("resumo", dados)
        print(f"  ok {len(dados['linhas'])} linhas, pregão {dados['pregao']}")
        for linha in dados["linhas"]:
            print(f"    {linha}")
        estado["resumo"] = {
            "situacao": "ok",
            "detalhe": f"{len(dados['linhas'])} linhas",
            "em": comum.agora(),
        }
    except comum.FonteIndisponivel as erro:
        comum.manter_anterior("resumo", str(erro))
        estado["resumo"] = {"situacao": "falhou", "detalhe": str(erro), "em": comum.agora()}

    print("\n[contratos] contratos em aberto (Boletim Diário da B3)")
    try:
        resumo = atualizar_contratos()
        houve_sucesso = True
        print(f"  ok {resumo}")
        estado["contratos"] = {"situacao": "ok", "detalhe": resumo, "em": comum.agora()}
    except comum.FonteIndisponivel as erro:
        comum.manter_anterior("contratos", str(erro))
        estado["contratos"] = {"situacao": "falhou", "detalhe": str(erro), "em": comum.agora()}

    print("\n[opcoes] posições em aberto por strike")
    try:
        dados = coletar_opcoes.coletar()
        houve_sucesso = True
        comum.gravar("opcoes", dados)
        resumo = (
            f"{dados['ativo']} a {dados['preco']}, vencimento {dados['vencimento']}, "
            f"{dados['series_no_vencimento']} séries"
        )
        print(f"  ok {resumo}")
        estado["opcoes"] = {"situacao": "ok", "detalhe": resumo, "em": comum.agora()}
    except comum.FonteIndisponivel as erro:
        comum.manter_anterior("opcoes", str(erro))
        estado["opcoes"] = {"situacao": "falhou", "detalhe": str(erro), "em": comum.agora()}

    atualizar_fontes(estado)

    # Guarda o dia no historico, para um dia dar para analisar a serie.
    # So anota o que e dado real: exemplo e dado velho ficam de fora, se
    # nao a serie ficaria com degraus que nao aconteceram no mercado.
    print("\n[historico] memória dos indicadores")
    try:
        print(f"  ok {historico.registrar()}")
    except OSError as erro:
        # Falhar aqui nao pode derrubar o painel: o historico e um extra.
        print(f"  ! não consegui gravar o histórico: {erro}")

    if not houve_sucesso:
        print("\nNenhuma fonte respondeu. Os arquivos anteriores foram mantidos.")
        return 1
    print("\nPronto.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
