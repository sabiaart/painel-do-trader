"""Roda o pipeline inteiro. E isto que o robo das 7h executa.

    python pipeline/atualizar.py

Cada fonte e tratada em separado. Se uma cair, as outras seguem e o arquivo
da que caiu fica como estava, marcado como desatualizado. O programa so
termina com erro se TODAS as fontes falharem - nesse caso vale avisar.
"""

from __future__ import annotations

import sys
from datetime import date

import calculos
import comum
import fontes

JANELA_VOL = 21  # pregoes usados na volatilidade historica


def atualizar_niveis() -> dict:
    """Coloca volatilidade real no movimento esperado de WIN e WDO.

    O ajuste anterior, a maxima e a minima continuam sendo exemplo: esses
    numeros vem dos arquivos de fim de dia da B3, que so entram na Fase 3.
    O que muda aqui e a LARGURA da faixa, que passa a ser real.
    """
    atual = comum.ler("niveis")
    if atual is None:
        raise comum.FonteIndisponivel("site/data/niveis.json sumiu")

    # Campo antigo: a volatilidade agora e descrita dentro de cada ativo.
    atual.pop("metodo_volatilidade", None)

    # Marcas deixadas por uma falha anterior. A fonte voltou, entao saem.
    atual.pop("motivo_falha", None)
    atual.pop("verificado_em", None)

    # Duas coisas que a tela nao pode afirmar enquanto nao forem calculadas
    # de verdade. Ao lado de uma volatilidade real, numero de exemplo engana.
    #
    # - faixa_ampliada: o pipeline ainda nao amplia a faixa em dia de evento.
    # - acertos: depende da maxima e da minima de cada pregao, que vem dos
    #   arquivos da B3, so na Fase 3.
    for ativo in atual["ativos"].values():
        ativo["faixa_ampliada"] = None
        ativo["acertos"] = None
        ativo["fechamento"] = None

    resultados = {}
    falhas = []

    # --- WDO: volatilidade do proprio dolar, do Banco Central ---
    try:
        serie = fontes.dolar_ptax()
        precos = [v for _, v in serie]
        vol = calculos.volatilidade_historica(precos, JANELA_VOL)
        # O WDO e cotado por mil dolares: 5,4212 no cambio = 5.421,2 no WDO.
        preco_wdo = precos[-1] * 1000
        atual["ativos"]["wdo"]["desvio"] = round(calculos.movimento_esperado(preco_wdo, vol), 1)
        atual["ativos"]["wdo"]["volatilidade"] = {
            "anual_pct": round(vol * 100, 1),
            "metodo": f"histórica de {JANELA_VOL} pregões",
            "fonte": "Banco Central (SGS 1, dólar PTAX de venda)",
            "data": serie[-1][0].isoformat(),
        }
        resultados["wdo"] = f"vol {vol * 100:.1f}% a.a. (PTAX de {serie[-1][0]:%d/%m})"
    except (comum.FonteIndisponivel, ValueError) as erro:
        falhas.append(f"dólar: {erro}")

    # --- WIN: volatilidade implicita do EWZ, via FRED ---
    # A especificacao manda usar o VIX do Ibovespa e deixa o VXEWZ como
    # reserva. O VIX do Ibovespa ainda depende de checar licenca (secao 10),
    # entao na Fase 2 fica a reserva, dita com todas as letras na tela.
    try:
        serie = fontes.vol_ewz()
        vol = serie[-1][1] / 100
        preco_win = atual["ativos"]["win"]["ajuste"]
        atual["ativos"]["win"]["desvio"] = round(calculos.movimento_esperado(preco_win, vol))
        atual["ativos"]["win"]["volatilidade"] = {
            "anual_pct": round(vol * 100, 1),
            "metodo": "implícita do EWZ (reserva do VIX do Ibovespa)",
            "fonte": "FRED / Cboe (VXEWZCLS)",
            "data": serie[-1][0].isoformat(),
        }
        resultados["win"] = f"vol {vol * 100:.1f}% a.a. (VXEWZ de {serie[-1][0]:%d/%m})"
    except (comum.FonteIndisponivel, ValueError, IndexError) as erro:
        falhas.append(f"VXEWZ: {erro}")

    if not resultados:
        raise comum.FonteIndisponivel("; ".join(falhas))

    # O ajuste ainda e exemplo, entao o aviso de exemplo continua de pe.
    atual.update(comum.cabecalho("Banco Central e FRED (volatilidade); ajustes ainda de exemplo", exemplo=True))
    atual["volatilidade_real"] = True
    atual["falhas"] = falhas
    comum.gravar("niveis", atual)
    return resultados


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

    atualizar_fontes(estado)

    if not houve_sucesso:
        print("\nNenhuma fonte respondeu. Os arquivos anteriores foram mantidos.")
        return 1
    print("\nPronto.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
