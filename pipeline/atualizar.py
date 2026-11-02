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

import calculos
import comum
import fontes
import indicadores

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

    atualizar_fontes(estado)

    if not houve_sucesso:
        print("\nNenhuma fonte respondeu. Os arquivos anteriores foram mantidos.")
        return 1
    print("\nPronto.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
