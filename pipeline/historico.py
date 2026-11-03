"""Memoria do painel: um registro por dia de cada indicador.

Para que serve
--------------
O painel mostra o hoje. Este arquivo guarda o ontem, para um dia dar para
perguntar coisas que so o tempo responde: o termometro antecipa queda? o
fluxo estrangeiro vira antes ou depois do preco? a faixa de movimento
esperado acerta mais quando a volatilidade esta alta?

Nada disso da para responder com o painel de hoje. So com uma serie.

O formato, e por que este
-------------------------
Um CSV longo, em `historico/indicadores.csv`:

    data;referencia;indicador;valor;unidade;fonte

`data` e o dia em que o painel rodou. `referencia` e o pregao a que o
numero se refere, que nem sempre e o mesmo: o fluxo estrangeiro chega com
dois dias uteis de atraso. Para analisar serie, use `referencia`; `data`
serve para saber quando aquilo esteve na tela.

Uma linha por indicador por dia, em vez de uma coluna por indicador. Parece
estranho, mas e o formato que nao quebra: quando um indicador novo aparece
(ou um some, como ja aconteceu com as posicoes por participante), o arquivo
continua valido e as linhas antigas continuam significando a mesma coisa.
Num arquivo de colunas, cada mudanca dessas exigiria reescrever o passado.

Abre no Excel, no bloco de notas e em qualquer biblioteca de analise.

Regravar o mesmo dia
--------------------
Rodar o painel tres vezes num dia nao cria tres registros: as linhas
daquele dia sao substituidas. O arquivo e sempre "um dia, um retrato".
"""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

import comum

PASTA = comum.RAIZ / "historico"
ARQUIVO = PASTA / "indicadores.csv"

CABECALHO = ["data", "referencia", "indicador", "valor", "unidade", "fonte"]


def _linhas_de_hoje() -> list[dict]:
    """Le os JSON que o pipeline acabou de gravar e vira linhas de CSV.

    Le do arquivo, e nao de variaveis passadas pelo pipeline, de proposito:
    assim o historico guarda exatamente o que o painel mostrou, nao o que
    o codigo pretendia mostrar.
    """
    linhas: list[dict] = []

    def anotar(indicador, valor, unidade="", fonte="", referencia=""):
        if valor is None:
            return
        linhas.append(
            {
                "referencia": referencia or "",
                "indicador": indicador,
                "valor": valor,
                "unidade": unidade,
                "fonte": fonte,
            }
        )

    # --- Placar dos indicadores ---
    placar = comum.ler("placar") or {}
    if not placar.get("exemplo") and not placar.get("desatualizado"):
        anotar("placar.favoraveis", placar.get("favoraveis"), "de " + str(placar.get("total")), placar.get("origem", ""), placar.get("pregao", ""))

    # --- Grade de mercados globais ---
    globais = comum.ler("globais") or {}
    if not globais.get("exemplo") and not globais.get("desatualizado"):
        for ativo in globais.get("ativos") or []:
            chave = _apelido(ativo.get("nome", ""))
            anotar(f"global.{chave}.variacao", ativo.get("variacao"), "%", globais.get("origem", ""), ativo.get("data", ""))

    # --- Niveis de WIN e WDO ---
    niveis = comum.ler("niveis") or {}
    if not niveis.get("exemplo") and not niveis.get("desatualizado"):
        for sigla, dados in (niveis.get("ativos") or {}).items():
            fonte = (dados.get("volatilidade") or {}).get("fonte", "")
            anotar(f"{sigla}.ajuste", dados.get("ajuste"), "pontos", fonte, dados.get("pregao", ""))
            anotar(f"{sigla}.volatilidade", (dados.get("volatilidade") or {}).get("anual_pct"), "% ao ano", fonte, dados.get("pregao", ""))
            anotar(f"{sigla}.desvio", dados.get("desvio"), "pontos", fonte, dados.get("pregao", ""))
            anotar(f"{sigla}.acertos", dados.get("acertos"), f"de {dados.get('janela')}", fonte, dados.get("pregao", ""))
            anotar(f"{sigla}.contrato", dados.get("contrato"), "", fonte, dados.get("pregao", ""))

    # --- Fluxo estrangeiro ---
    fluxo = comum.ler("fluxo") or {}
    if not fluxo.get("exemplo") and not fluxo.get("desatualizado"):
        # A serie inteira, nao so o ultimo dia: a B3 publica cerca de 21
        # pregoes de uma vez, e jogar fora os 18 anteriores seria esperar
        # um mes para ter o que ja esta na mao.
        for dia, valor in zip(fluxo.get("datas") or [], fluxo.get("pregoes") or []):
            anotar("fluxo.estrangeiro.dia", valor, "R$ bi", fluxo.get("origem", ""), dia)
        anotar("fluxo.estrangeiro.mes", fluxo.get("mes"), "R$ bi", fluxo.get("origem", ""), fluxo.get("pregao", ""))
    
    # --- Contratos em aberto ---
    contratos = comum.ler("contratos") or {}
    if not contratos.get("exemplo") and not contratos.get("desatualizado"):
        for contrato in contratos.get("contratos") or []:
            sigla = contrato.get("nome", "").split(" ")[0]
            anotar(f"{sigla}.em_aberto", contrato.get("contratos"), "contratos", contratos.get("origem", ""), contratos.get("pregao", ""))

    # --- Termometro ---
    termometro = comum.ler("termometro") or {}
    if not termometro.get("exemplo") and not termometro.get("desatualizado"):
        fonte = termometro.get("origem", "")
        anotar("termometro.nota", termometro.get("nota"), "0 a 100", fonte)
        anotar("termometro.zona", termometro.get("zona"), "", fonte)
        anotar("termometro.componentes_usados", termometro.get("usados"), f"de {termometro.get('previstos')}", fonte)
        for componente in termometro.get("componentes") or []:
            if componente.get("nota") is None:
                continue
            anotar(
                f"termometro.{_apelido(componente['nome'])}",
                componente["nota"],
                "0 a 100",
                componente.get("fonte", ""),
            )

    return linhas


def _apelido(nome: str) -> str:
    """"Volatilidade (VXEWZ)" -> "volatilidade_vxewz". Nome de coluna
    estavel, sem acento nem pontuacao, para a analise nao sofrer depois."""
    from planilha import sem_acento

    limpo = sem_acento(nome)
    saida = "".join(c if c.isalnum() else "_" for c in limpo)
    while "__" in saida:
        saida = saida.replace("__", "_")
    return saida.strip("_")


def _existentes() -> list[dict]:
    if not ARQUIVO.exists():
        return []
    with ARQUIVO.open(encoding="utf-8", newline="") as arquivo:
        return [linha for linha in csv.DictReader(arquivo, delimiter=";")]


def registrar(quando: date | None = None) -> str:
    """Anota o dia de hoje no historico. Devolve um resumo para o log."""
    quando = quando or date.today()
    hoje = quando.isoformat()

    novas = _linhas_de_hoje()
    if not novas:
        return "nenhum indicador real para anotar hoje"
    for linha in novas:
        linha["data"] = hoje

    # Substitui o dia, em vez de empilhar: rodar duas vezes nao duplica.
    guardadas = [linha for linha in _existentes() if linha.get("data") != hoje]
    todas = guardadas + novas
    todas.sort(key=lambda linha: (linha.get("data", ""), linha.get("indicador", "")))

    PASTA.mkdir(parents=True, exist_ok=True)
    temporario = ARQUIVO.with_suffix(".csv.tmp")
    with temporario.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, CABECALHO, delimiter=";", extrasaction="ignore")
        escritor.writeheader()
        escritor.writerows(todas)
    temporario.replace(ARQUIVO)

    dias = len({linha.get("data") for linha in todas})
    return f"{len(novas)} indicadores de hoje, {len(todas)} linhas em {dias} dias"
