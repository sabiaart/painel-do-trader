"""Le os arquivos da B3 que voce baixou a mao.

Por que isto e manual
---------------------
A B3 escreve nos termos do site dela que "e expressamente vedada a coleta
automatizada, inclusive por meio de ferramentas de inteligencia artificial".
Entao o robo deste projeto NUNCA acessa b3.com.br. Ele so le arquivos que
ja estao no seu computador, dentro da pasta `b3-manual`.

As instrucoes de onde baixar cada arquivo estao em `b3-manual/LEIA-ME.md`.

Como a leitura funciona
-----------------------
Nao dependemos de coluna fixa nem de nome de arquivo. A B3 muda o layout
das planilhas de vez em quando, e um leitor amarrado em "coluna D, linha 12"
quebraria calado - o que e pior do que nao ler.

Em vez disso procuramos por PALAVRA:

  1. a data do pregao, em qualquer celula (dd/mm/aaaa ou aaaa-mm-dd);
  2. a linha de cada tipo de participante, pelo nome dele;
  3. o saldo dentro dessa linha, pelo titulo da coluna - e, se nao houver
     titulo reconhecivel, pelo ultimo numero da linha.

Cada leitura imprime o que encontrou e de qual celula tirou, para dar para
conferir contra a planilha aberta na tela.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path

import comum
from planilha import PlanilhaIlegivel, ler_planilha, numero, sem_acento

ENTRADA = comum.RAIZ / "b3-manual"
HISTORICO = ENTRADA / "historico.json"

LIDOS = ENTRADA / "ja-lidos"

# Os quatro tipos de participante que o painel mostra, e as palavras que a
# B3 usa para cada um. "nao residente" e o nome oficial do estrangeiro.
PARTICIPANTES = [
    ("estrangeiro", "Estrangeiro", ("nao residente", "estrangeiro", "nao-residente")),
    ("institucional", "Institucional", ("institucional", "investidor institucional")),
    ("pessoa_fisica", "Pessoa física", ("pessoa fisica", "pessoas fisicas", "individual")),
    ("financeira", "Inst. financeira", ("instituicao financeira", "instituicoes financeiras")),
]

# Titulos de coluna que valem como saldo liquido, em ordem de preferencia.
TITULOS_SALDO = ("saldo", "liquido", "net", "posicao liquida", "resultado")

DATA_BR = re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b")
DATA_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")


class SemArquivo(Exception):
    """Nao ha arquivo novo nessa pasta. Nao e erro: e so nao ter o que ler."""


# ---------------------------------------------------------------- utilidades


def _arquivos(subpasta: str) -> list[Path]:
    """Planilhas dentro de b3-manual/<subpasta>, da mais antiga para a mais
    nova. Ignora a pasta `ja-lidos` e arquivos temporarios do Excel."""
    pasta = ENTRADA / subpasta
    # Cria a pasta se nao existir: o .gitignore mantem o conteudo dela fora
    # do repositorio, entao num computador novo ela nao vem junto. Melhor
    # ela aparecer sozinha do que o usuario ter que adivinhar o nome.
    pasta.mkdir(parents=True, exist_ok=True)
    aceitos = (".csv", ".txt", ".xlsx", ".xlsm", ".xls")
    achados = [
        a
        for a in pasta.iterdir()
        if a.is_file() and a.suffix.lower() in aceitos and not a.name.startswith("~$")
    ]
    if not achados:
        raise SemArquivo(f"nenhuma planilha em b3-manual/{subpasta}")
    return sorted(achados, key=lambda a: (a.stat().st_mtime, a.name))


def _achar_data(linhas: list[list[str]]) -> date | None:
    """Primeira data que aparecer na planilha, em qualquer celula.

    A B3 escreve a data do pregao no cabecalho do arquivo, nao numa coluna,
    e a posicao muda entre os relatorios.
    """
    for linha in linhas[:40]:
        for celula in linha:
            texto = str(celula)
            achado = DATA_BR.search(texto)
            if achado:
                dia, mes, ano = achado.groups()
                try:
                    return date(int(ano), int(mes), int(dia))
                except ValueError:
                    continue
            achado = DATA_ISO.search(texto)
            if achado:
                try:
                    return date.fromisoformat(achado.group(0))
                except ValueError:
                    continue
            # Celula de data em .xlsx vem como numero de serie do Excel.
            valor = numero(texto)
            if valor and 40000 < valor < 60000 and len(texto) <= 12:
                try:
                    base = datetime(1899, 12, 30).date()
                    return base.fromordinal(base.toordinal() + int(valor))
                except (ValueError, OverflowError):
                    continue
    return None


def _coluna_do_saldo(linhas: list[list[str]], ate: int) -> int | None:
    """Em qual coluna esta o saldo, olhando os titulos acima dos dados."""
    for linha in reversed(linhas[:ate]):
        for posicao, celula in enumerate(linha):
            titulo = sem_acento(celula)
            if titulo and any(t in titulo for t in TITULOS_SALDO):
                return posicao
    return None


def _valor_da_linha(linha: list[str], coluna: int | None) -> tuple[float, str] | None:
    """Tira o numero da linha. Devolve (valor, de onde veio) para o log."""
    if coluna is not None and coluna < len(linha):
        valor = numero(linha[coluna])
        if valor is not None:
            return valor, f"coluna {coluna + 1} (titulo de saldo)"

    # Sem titulo reconhecivel: o saldo liquido e, nestes relatorios, sempre
    # a ultima coluna numerica da linha (compras, vendas, saldo).
    for posicao in range(len(linha) - 1, -1, -1):
        valor = numero(linha[posicao])
        if valor is not None:
            return valor, f"coluna {posicao + 1} (ultimo numero da linha)"
    return None


def _ler_participantes(caminho: Path) -> tuple[date, dict[str, float], list[str]]:
    """Le uma planilha e devolve a data e o saldo de cada participante."""
    linhas = ler_planilha(caminho)
    if not linhas:
        raise PlanilhaIlegivel(f"{caminho.name} esta vazio")

    quando = _achar_data(linhas)
    if quando is None:
        raise PlanilhaIlegivel(
            f"{caminho.name}: nao achei a data do pregao em nenhuma celula. "
            "Confira se baixou a planilha certa."
        )

    saldos: dict[str, float] = {}
    log: list[str] = []
    for posicao, linha in enumerate(linhas):
        primeiras = sem_acento(" ".join(linha[:3]))
        if not primeiras:
            continue
        for chave, _, palavras in PARTICIPANTES:
            if chave in saldos:
                continue
            if not any(p in primeiras for p in palavras):
                continue
            coluna = _coluna_do_saldo(linhas, posicao)
            achado = _valor_da_linha(linha, coluna)
            if achado is None:
                continue
            valor, origem = achado
            saldos[chave] = valor
            log.append(f"linha {posicao + 1}, {origem}: {chave} = {valor:,.0f}")

    if not saldos:
        titulos = " | ".join(c for c in linhas[0][:8] if c) or "(primeira linha vazia)"
        raise PlanilhaIlegivel(
            f"{caminho.name}: nao achei nenhum tipo de participante. "
            f"A primeira linha do arquivo e: {titulos}"
        )
    return quando, saldos, log


# ------------------------------------------------------------------ historico


def _historico() -> dict:
    """Memoria local: um saldo por data, acumulado a cada arquivo lido.

    Precisamos disto porque cada download da B3 traz UM pregao, e o grafico
    de fluxo mostra vinte. Sem acumular, voce teria que baixar vinte
    arquivos todo dia.
    """
    if not HISTORICO.exists():
        return {"fluxo": {}, "participantes": {}}
    try:
        dados = json.loads(HISTORICO.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"fluxo": {}, "participantes": {}}
    dados.setdefault("fluxo", {})
    dados.setdefault("participantes", {})
    return dados


def _gravar_historico(dados: dict) -> None:
    ENTRADA.mkdir(parents=True, exist_ok=True)
    temporario = HISTORICO.with_suffix(".json.tmp")
    temporario.write_text(
        json.dumps(dados, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporario.replace(HISTORICO)


def _arquivar(caminho: Path) -> None:
    """Move o arquivo lido para `ja-lidos`, para a pasta de entrada ficar
    sempre limpa e voce saber o que ainda falta baixar."""
    destino = LIDOS / caminho.parent.name
    destino.mkdir(parents=True, exist_ok=True)
    alvo = destino / caminho.name
    if alvo.exists():
        alvo.unlink()
    caminho.replace(alvo)


# --------------------------------------------------------------------- fluxo


def atualizar_fluxo() -> str:
    """Bloco "Fluxo estrangeiro": barras dos ultimos 20 pregoes, em R$ bi."""
    arquivos = _arquivos("fluxo")
    historico = _historico()
    novos = 0
    avisos: list[str] = []

    for caminho in arquivos:
        quando, saldos, log = _ler_participantes(caminho)
        if "estrangeiro" not in saldos:
            avisos.append(f"{caminho.name}: achei a planilha mas nao a linha do estrangeiro")
            continue
        bruto = saldos["estrangeiro"]
        bilhoes, nota = _em_bilhoes(bruto)
        historico["fluxo"][quando.isoformat()] = round(bilhoes, 3)
        novos += 1
        print(f"    {caminho.name}: pregão {quando:%d/%m/%Y}, {bilhoes:+.2f} R$ bi ({nota})")
        for linha in log:
            print(f"      {linha}")
        _arquivar(caminho)

    if not novos:
        raise comum.FonteIndisponivel("; ".join(avisos) or "nenhum arquivo de fluxo pôde ser lido")

    _gravar_historico(historico)

    serie = sorted(historico["fluxo"].items())
    ultimos = serie[-20:]
    valores = [v for _, v in ultimos]

    # Somar zero pregao e dar zero: a tela mostraria "Mes +0,0", que se le
    # como "nao houve fluxo", quando a verdade e "nao ha dado". None vira
    # travessao na tela.
    hoje = date.today()
    do_mes = _soma(serie, f"{hoje:%Y-%m}")
    do_ano = _soma(serie, f"{hoje:%Y}")

    dados = comum.cabecalho("B3, participação dos investidores (download manual)")
    dados["unidade"] = "R$ bi"
    dados["pregoes"] = valores
    dados["ontem"] = valores[-1]
    dados["mes"] = do_mes
    dados["ano"] = do_ano
    dados["pregao"] = ultimos[-1][0]
    dados["pregoes_no_historico"] = len(serie)
    # Transparencia: o mes e o ano somam so os pregoes que VOCE baixou.
    dados["parcial"] = len(serie) < 20
    comum.gravar("fluxo", dados)

    parcial = f"; histórico ainda tem só {len(serie)} pregões" if len(serie) < 20 else ""
    return f"{novos} arquivo(s) lido(s), último pregão {ultimos[-1][0]}{parcial}"


def _soma(serie: list[tuple[str, float]], prefixo: str) -> float | None:
    """Soma os pregoes cuja data comeca com `prefixo` ("2026-11" ou "2026").
    Devolve None quando nao ha nenhum, em vez de zero."""
    valores = [v for d, v in serie if d.startswith(prefixo)]
    return round(sum(valores), 2) if valores else None


def _em_bilhoes(bruto: float) -> tuple[float, str]:
    """A B3 publica esse saldo em reais; algumas planilhas, em milhares.

    Em vez de adivinhar pelo nome do arquivo, decide pela ordem de
    grandeza e DIZ qual regra usou, para dar para desconfiar.

    Um saldo diario de fluxo estrangeiro na Bovespa fica na casa de centenas
    de milhoes a poucos bilhoes de reais.
    """
    absoluto = abs(bruto)
    if absoluto >= 1e8:
        return bruto / 1e9, "lido em reais"
    if absoluto >= 1e5:
        return bruto / 1e6, "lido em milhares de reais"
    if absoluto >= 100:
        return bruto / 1e3, "lido em milhões de reais"
    return bruto, "lido já em bilhões"


# -------------------------------------------------------------- participantes


def atualizar_participantes() -> str:
    """Bloco "Quem está comprado no WIN": saldo de contratos por tipo."""
    arquivos = _arquivos("participantes")
    historico = _historico()
    novos = 0

    for caminho in arquivos:
        quando, saldos, log = _ler_participantes(caminho)
        historico["participantes"][quando.isoformat()] = {
            k: round(v) for k, v in saldos.items()
        }
        novos += 1
        print(f"    {caminho.name}: pregão {quando:%d/%m/%Y}, {len(saldos)} participantes")
        for linha in log:
            print(f"      {linha}")
        _arquivar(caminho)

    if not novos:
        raise comum.FonteIndisponivel("nenhum arquivo de participantes pôde ser lido")

    _gravar_historico(historico)

    serie = sorted(historico["participantes"].items())
    quando, atuais = serie[-1]
    # Cinco pregoes atras, para a direcao da seta. Com menos historico que
    # isso, compara com o que houver.
    anterior = serie[-6][1] if len(serie) >= 6 else (serie[0][1] if len(serie) > 1 else {})

    lista = []
    for chave, rotulo, _ in PARTICIPANTES:
        if chave not in atuais:
            continue
        saldo = atuais[chave]
        antes = anterior.get(chave)
        lista.append(
            {
                "nome": rotulo,
                "saldo": saldo,
                # Sem pregao anterior nao ha direcao. "sobe" por omissao
                # desenharia uma seta verde dizendo "subiu" sem nada atras.
                "direcao": None if antes is None else ("sobe" if saldo >= antes else "desce"),
                "variacao_5d": None if antes is None else saldo - antes,
            }
        )

    dados = comum.cabecalho("B3, posições em aberto por tipo de participante (download manual)")
    dados["participantes"] = lista
    dados["pregao"] = quando
    dados["leitura"] = _leitura(lista, anterior)
    dados["pregoes_no_historico"] = len(serie)
    dados["parcial"] = len(serie) < 6
    comum.gravar("participantes", dados)

    return f"{novos} arquivo(s) lido(s), pregão {quando}, {len(lista)} participantes"


def _leitura(lista: list[dict], anterior: dict) -> str:
    """Uma frase descrevendo o que mudou. Estatistica, nunca conselho.

    Nao diz o que fazer nem para onde o mercado vai: so le o numero em
    voz alta, como manda a regra do projeto.
    """
    estrangeiro = next((p for p in lista if p["nome"] == "Estrangeiro"), None)
    if estrangeiro is None:
        return "sem dados do investidor estrangeiro neste pregão"

    saldo = estrangeiro["saldo"]
    lado = "comprada" if saldo > 0 else "vendida"
    variacao = estrangeiro.get("variacao_5d")

    if not anterior or variacao is None:
        return f"estrangeiro com posição {lado} de {abs(saldo):,.0f} contratos".replace(",", ".")

    if (saldo > 0) == (variacao > 0):
        movimento = "ampliou"
    else:
        movimento = "reduziu"
    return (
        f"estrangeiro {movimento} a posição {lado} em "
        f"{abs(variacao):,.0f} contratos nos últimos pregões".replace(",", ".")
    )
