"""Tabelas do Boletim Diario do Mercado, da B3.

AVISO, e e importante que ele fique escrito aqui
------------------------------------------------
A pagina do Boletim Diario diz, com todas as letras:

    "Os dados e informacoes disponibilizados nesta pagina sao de propriedade
    exclusiva da B3 e destinam-se estritamente a consulta informativa (...)
    e expressamente vedada a coleta automatizada, inclusive por meio de
    ferramentas de inteligencia artificial, para quaisquer finalidades,
    comerciais ou nao, proprias ou de terceiros."

Este arquivo faz exatamente a coleta automatizada que essa frase proibe. O
dono do projeto leu o texto acima e decidiu seguir assim mesmo, para uso
pessoal, com os dados ficando no computador dele e sem republicacao.

Quem mexer neste codigo depois precisa saber disso. Se um dia o painel
virar site publico, isto aqui tem de sair antes.

Como a coleta se comporta
-------------------------
Ja que estamos aqui, estamos da forma menos incomoda possivel para o
servidor da B3 - que e, afinal, a razao declarada da proibicao
("manutencao da seguranca do site e integridade dos dados"):

- cada dia e baixado UMA vez na vida e guardado em `cache-b3/`;
- rodar o painel de novo no mesmo dia nao gera pedido nenhum;
- pausa entre pedidos;
- so dias uteis, consultados na propria lista de dias uteis da B3.

A API
-----
    GET  /bdi/table/workdays?date=AAAA-MM-DD     lista de pregoes
    POST /bdi/table/{tabela}/{de}/{ate}/{pag}/{n}   dados da tabela

A resposta traz `columns` (com o nome de cada coluna) e `values` (as
linhas), o que permite achar a coluna pelo nome em vez de pela posicao.
"""

from __future__ import annotations

import json
import re
import time
from datetime import date, datetime
from pathlib import Path

import comum

BASE = "https://arquivos.b3.com.br/bdi"
CACHE = comum.RAIZ / "cache-b3"

PAUSA = 1.5  # segundos entre pedidos

# "Dados acumulados do inicio do mes ate o dia 28/10/2026."
ATE_O_DIA = re.compile(r"at[ée]\s+o\s+dia\s+(\d{2})/(\d{2})/(\d{4})")


def _pedir(caminho: str, *, metodo: str = "GET") -> object:
    bruto = comum.baixar(f"{BASE}/{caminho}", metodo=metodo)
    try:
        return json.loads(bruto.decode("utf-8"))
    except json.JSONDecodeError as erro:
        raise comum.FonteIndisponivel(f"B3 {caminho}: resposta nao e JSON ({erro})") from erro


def dias_uteis(ate: date | None = None) -> list[date]:
    """Pregoes ate a data, do mais recente para o mais antigo.

    E a propria lista da B3: evita ter que saber os feriados da bolsa, que
    nao sao os feriados do calendario.
    """
    ate = ate or date.today()
    bruto = _pedir(f"table/workdays?date={ate.isoformat()}")
    if not isinstance(bruto, list):
        raise comum.FonteIndisponivel("B3 workdays: esperava uma lista")
    dias = []
    for item in bruto:
        try:
            dias.append(datetime.fromisoformat(str(item)).date())
        except ValueError:
            continue
    if not dias:
        raise comum.FonteIndisponivel("B3 workdays: lista vazia")
    return dias


PAGINA_GRANDE = 1000  # maximo que a API aceita; 5000 e recusado


def tabela_paginada(nome: str, dia: date, *, maximo_paginas: int = 60) -> list[list]:
    """Todas as linhas de uma tabela grande, juntando as paginas.

    Tabelas como as posicoes em aberto tem ~43 mil linhas por dia, em 43
    paginas de mil. Nao da para filtrar no servidor: o campo de ticker do
    site da B3 filtra no navegador, sobre o que ja foi carregado.

    Cada pagina vai para o cache separadamente. Entao o custo e de 43
    pedidos no PRIMEIRO acesso de cada dia e zero nos seguintes.
    """
    linhas: list[list] = []
    pagina = 1
    while pagina <= maximo_paginas:
        resposta = tabela(nome, dia, pagina=pagina, limite=PAGINA_GRANDE)
        t = resposta["table"]
        linhas.extend(t.get("values") or [])
        total = t.get("pageCount") or 1
        if pagina >= total:
            break
        pagina += 1
    return linhas


def colunas_de(nome: str, dia: date) -> list[dict]:
    """Os cabecalhos da tabela, para casar coluna por rotulo."""
    return tabela(nome, dia, pagina=1, limite=PAGINA_GRANDE)["table"]["columns"]


def tabela(nome: str, dia: date, *, limite: int = 500, pagina: int = 1) -> dict:
    """Uma tabela do boletim, num dia. Baixa so se ainda nao estiver no cache."""
    sufixo = "" if pagina == 1 and limite == 500 else f"-p{pagina}-{limite}"
    guardado = CACHE / nome / f"{dia.isoformat()}{sufixo}.json"
    if guardado.exists():
        try:
            return json.loads(guardado.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            guardado.unlink()  # cache corrompido: baixa de novo

    d = dia.isoformat()
    resposta = _pedir(f"table/{nome}/{d}/{d}/{pagina}/{limite}", metodo="POST")
    if not isinstance(resposta, dict) or "table" not in resposta:
        raise comum.FonteIndisponivel(f"B3 {nome} em {d}: resposta sem tabela")

    guardado.parent.mkdir(parents=True, exist_ok=True)
    guardado.write_text(json.dumps(resposta, ensure_ascii=False), encoding="utf-8", newline="\n")
    time.sleep(PAUSA)
    return resposta


def _coluna(t: dict, *pedacos: str) -> int:
    """Posicao da coluna cujo ROTULO contem um dos pedacos de texto.

    Usamos o rotulo (`friendlyNamePt`), nao o nome interno (`name`), porque
    na tabela de participacao dos investidores os nomes internos estao
    desalinhados com o conteudo: a coluna chamada "Sales" e a de
    porcentagem, e as vendas estao numa chamada "Partmil". Confiar no nome
    interno trocaria vendas por porcentagem sem reclamar.
    """
    from planilha import sem_acento

    for i, coluna in enumerate(t.get("columns", [])):
        rotulo = sem_acento(coluna.get("friendlyNamePt") or coluna.get("friendlyName") or "")
        if any(sem_acento(p) in rotulo for p in pedacos):
            return i
    raise comum.FonteIndisponivel(
        f"coluna {pedacos[0]!r} não existe em {t.get('friendlyNamePt')}; "
        f"tem {[c.get('friendlyNamePt') for c in t.get('columns', [])]}"
    )


def data_de_referencia(t: dict) -> date | None:
    """O dia a que os numeros se referem, que NAO e o dia do arquivo.

    O texto da tabela diz "Dados acumulados do inicio do mes ate o dia
    28/10/2026" - e esse 28/10 que vale. O arquivo de 30/10 traz 28/10;
    o de 02/10 traz 30/09, ou seja, ainda o mes anterior.

    Ignorar isso datava o grafico inteiro errado, com dois dias de deslocamento
    e um mes trocado na virada.
    """
    for texto in t.get("texts") or []:
        achado = ATE_O_DIA.search(str(texto.get("textPt") or ""))
        if achado:
            dia, mes, ano = achado.groups()
            try:
                return date(int(ano), int(mes), int(dia))
            except ValueError:
                continue
    return None


def participacao_investidores(dia: date) -> tuple[date, dict[str, tuple[float, float]]]:
    """Compras e vendas por tipo de investidor, em R$ mil, ACUMULADAS no mes.

    Devolve (data de referencia, {tipo: (compras, vendas)}).

    Atencao: os valores sao acumulados desde o primeiro pregao do mes. Para
    ter o fluxo de um dia e preciso subtrair o dia anterior - e isso so vale
    dentro do mesmo mes, porque na virada o acumulado volta a zero.
    """
    t = tabela("SharesInvesVolum", dia)["table"]
    referencia = data_de_referencia(t)
    if referencia is None:
        raise comum.FonteIndisponivel(
            f"participação dos investidores de {dia}: não achei a data de referência no texto"
        )

    c_tipo = _coluna(t, "tipos de investidores", "investidor")
    c_compra = _coluna(t, "compras")
    c_venda = _coluna(t, "vendas")

    saida: dict[str, tuple[float, float]] = {}
    for linha in t.get("values") or []:
        try:
            tipo = str(linha[c_tipo])
            saida[tipo] = (float(linha[c_compra]), float(linha[c_venda]))
        except (IndexError, TypeError, ValueError):
            continue

    if not saida:
        raise comum.FonteIndisponivel(f"participação dos investidores de {dia}: tabela vazia")
    return referencia, saida


ESTRANGEIRO = "strangeiro"  # "Investidor Estrangeiro", sem depender do acento


def fluxo_estrangeiro_diario(limite: int = 24) -> list[tuple[date, float]]:
    """Saldo diario do investidor estrangeiro, em R$ bi, do mais antigo
    para o mais novo.

    A tabela da B3 e ACUMULADA no mes. O saldo de um dia e, portanto, o
    acumulado dele menos o acumulado do pregao anterior:

        dia 27 acumulado:  R$ 690 bi
        dia 28 acumulado:  R$ 736 bi
        dia 28 sozinho:    R$  46 bi

    Duas armadilhas, as duas tratadas aqui:

    1. A data do arquivo nao e a data do dado (ha dois dias uteis de
       atraso). Usamos a data que a propria tabela declara no texto.
    2. Na virada do mes o acumulado volta a zero. Subtrair o ultimo dia do
       mes anterior daria um numero gigante e negativo. No primeiro pregao
       do mes o acumulado JA E o saldo do dia, e e usado direto.
    """
    pregoes = dias_uteis()
    acumulado: dict[date, float] = {}

    for dia in pregoes[:limite]:
        try:
            referencia, tipos = participacao_investidores(dia)
        except comum.FonteIndisponivel:
            continue  # um dia sem publicacao nao invalida a serie
        for tipo, (compras, vendas) in tipos.items():
            if ESTRANGEIRO in tipo:
                acumulado[referencia] = compras - vendas
                break

    if not acumulado:
        raise comum.FonteIndisponivel("nenhum pregão com participação dos investidores")

    # Primeiro pregao de cada mes, segundo o calendario da propria B3.
    primeiro_do_mes = {}
    for dia in sorted(pregoes):
        primeiro_do_mes.setdefault((dia.year, dia.month), dia)

    serie: list[tuple[date, float]] = []
    datas = sorted(acumulado)
    for posicao, dia in enumerate(datas):
        anterior = datas[posicao - 1] if posicao else None
        if anterior and (anterior.year, anterior.month) == (dia.year, dia.month):
            saldo = acumulado[dia] - acumulado[anterior]
        elif primeiro_do_mes.get((dia.year, dia.month)) == dia:
            saldo = acumulado[dia]  # primeiro pregao: o acumulado e o dia
        else:
            continue  # falta o dia anterior do mesmo mes; nao da para isolar
        serie.append((dia, saldo / 1e6))  # R$ mil -> R$ bi

    if not serie:
        raise comum.FonteIndisponivel(
            "não consegui isolar nenhum pregão: faltam dias consecutivos do mesmo mês"
        )
    return serie


def _indice(colunas: list[dict], *pedacos: str) -> int:
    from planilha import sem_acento

    for i, coluna in enumerate(colunas):
        rotulo = sem_acento(coluna.get("friendlyNamePt") or coluna.get("friendlyName") or "")
        if any(sem_acento(p) in rotulo for p in pedacos):
            return i
    raise comum.FonteIndisponivel(
        f"coluna {pedacos[0]!r} sumiu; tem {[c.get('friendlyNamePt') for c in colunas]}"
    )


def posicoes_em_aberto_opcoes(dia: date, ativos: set[str]) -> dict[str, dict]:
    """Posicoes em aberto das opcoes dos ativos pedidos, por serie.

    Atencao a uma pegadinha: para OPCAO a coluna "Contratos em aberto" vem
    vazia. O numero que vale e "Total de posicoes". Usar a primeira daria
    uma tabela inteira de zeros, sem erro nenhum na tela.
    """
    colunas = colunas_de("OpenPositionsEquities", dia)
    c_papel = _indice(colunas, "instrumento financeiro")
    c_ativo = _indice(colunas, "ativo")
    c_segmento = _indice(colunas, "segmento")
    c_posicoes = _indice(colunas, "total de posicoes")

    saida: dict[str, dict] = {}
    for linha in tabela_paginada("OpenPositionsEquities", dia):
        try:
            if str(linha[c_ativo]) not in ativos:
                continue
            segmento = str(linha[c_segmento] or "").upper()
            if "CALL" not in segmento and "PUT" not in segmento:
                continue
            posicoes = linha[c_posicoes]
            if not posicoes:
                continue
            saida[str(linha[c_papel])] = {
                "ativo": str(linha[c_ativo]),
                "tipo": "call" if "CALL" in segmento else "put",
                "posicoes": int(posicoes),
            }
        except (IndexError, TypeError, ValueError):
            continue
    if not saida:
        raise comum.FonteIndisponivel(
            f"nenhuma opção em aberto de {', '.join(sorted(ativos))} em {dia}"
        )
    return saida


CADASTRO = CACHE / "cadastro-opcoes.json"


def cadastro_opcoes(dia: date, papeis: set[str]) -> dict[str, dict]:
    """Strike, tipo e vencimento de cada serie pedida.

    O cadastro de uma serie nao muda: o strike da BOVAK240W2 e o mesmo
    hoje e daqui a um mes. Entao ele e guardado para sempre em disco, e a
    tabela de 81 paginas so e varrida quando aparece serie desconhecida -
    o que acontece quando a B3 cria vencimentos novos, nao todo dia.
    """
    guardado: dict = {}
    if CADASTRO.exists():
        try:
            guardado = json.loads(CADASTRO.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            guardado = {}
    conhecidas: dict[str, dict] = guardado.get("series") or {}

    faltando = {p for p in papeis if not conhecidas.get(p)}
    # Varre no maximo uma vez por dia. Series que faltam hoje podem
    # aparecer no cadastro de amanha - ja aconteceu de a B3 informar
    # 10 milhoes de contratos em aberto numa serie que o cadastro do
    # mesmo dia nao lista. Marcar como inexistente para sempre perderia
    # essa serie quando ela voltasse; varrer a cada execucao seria
    # 81 paginas por nada.
    if not faltando or guardado.get("ultima_varredura") == dia.isoformat():
        return {p: conhecidas[p] for p in papeis if conhecidas.get(p)}

    print(f"    cadastro: {len(faltando)} séries novas, varrendo o cadastro da B3")
    colunas = colunas_de("InstrumentsEquities", dia)
    c_papel = _indice(colunas, "instrumento financeiro")
    c_expira = _indice(colunas, "data de expiracao")
    c_tipo = _indice(colunas, "tipo de opcao")
    c_strike = _indice(colunas, "preco de exercicio")
    c_estilo = _indice(colunas, "estilo de opcao")

    for linha in tabela_paginada("InstrumentsEquities", dia, maximo_paginas=120):
        try:
            papel = str(linha[c_papel])
            if papel not in faltando:
                continue
            strike = linha[c_strike]
            if not strike:
                continue
            conhecidas[papel] = {
                "strike": float(strike),
                "tipo_b3": str(linha[c_tipo] or ""),
                "vencimento": str(linha[c_expira] or "")[:10],
                "estilo": str(linha[c_estilo] or ""),
            }
        except (IndexError, TypeError, ValueError):
            continue

    CADASTRO.parent.mkdir(parents=True, exist_ok=True)
    CADASTRO.write_text(
        json.dumps(
            {"series": conhecidas, "ultima_varredura": dia.isoformat()}, ensure_ascii=False
        ),
        encoding="utf-8",
        newline="\n",
    )
    achadas = sum(1 for p in faltando if conhecidas.get(p))
    if achadas < len(faltando):
        print(f"    cadastro: {len(faltando) - achadas} séries seguem sem strike na B3")
    return {p: conhecidas[p] for p in papeis if conhecidas.get(p)}


def valor_de_etf(dia: date, codigo: str) -> float:
    """Ultimo preco de referencia de um ETF, da tabela IOPV.

    O BOVA11 nao aparece na tabela de negocios consolidados - ela traz as
    opcoes e um punhado de papeis, nao os ETFs. O IOPV traz, em UMA pagina
    de 70 linhas, o que custaria 74 paginas pelo outro caminho.

    Ressalva: o IOPV e o valor de referencia da cesta do ETF, nao o preco
    negociado. Nos dois anda junto por centavos, mas nao sao a mesma coisa.
    """
    t = tabela("IOPV", dia, pagina=1, limite=PAGINA_GRANDE)["table"]
    c_codigo = _indice(t["columns"], "codigo if", "codigo")
    c_ultimo = _indice(t["columns"], "ultimo preco")
    for linha in t.get("values") or []:
        try:
            if str(linha[c_codigo]).strip().upper() == codigo.upper():
                return float(linha[c_ultimo])
        except (IndexError, TypeError, ValueError):
            continue
    raise comum.FonteIndisponivel(f"{codigo} não está na tabela IOPV de {dia}")


def fechamentos(dia: date, papeis: set[str]) -> dict[str, float]:
    """Preco de fechamento dos papeis pedidos (acao, ETF ou opcao)."""
    colunas = colunas_de("ConsolidatedTradesEquities", dia)
    c_papel = _indice(colunas, "instrumento financeiro")
    c_fecha = _indice(colunas, "preco de fechamento")

    saida: dict[str, float] = {}
    for linha in tabela_paginada("ConsolidatedTradesEquities", dia, maximo_paginas=120):
        try:
            papel = str(linha[c_papel])
            if papel in papeis and linha[c_fecha]:
                saida[papel] = float(linha[c_fecha])
        except (IndexError, TypeError, ValueError):
            continue
    return saida


def contratos_em_aberto_serie(limite: int = 21) -> list[tuple[date, dict[str, dict]]]:
    """Contratos em aberto dos ultimos pregoes, do mais antigo para o mais novo.

    A B3 nao publica historico desta tabela: so o dia. O historico e nosso,
    montado em `cache-b3/` um dia por vez. Por isso a primeira execucao
    busca varios dias e as seguintes buscam so o que falta.
    """
    serie = []
    for dia in dias_uteis()[:limite]:
        try:
            referencia, ativos = contratos_em_aberto(dia)
        except comum.FonteIndisponivel:
            continue
        serie.append((referencia, ativos))
    if not serie:
        raise comum.FonteIndisponivel("nenhum pregão com quadro analítico")
    serie.sort(key=lambda par: par[0])
    return serie


def contratos_em_aberto(dia: date) -> tuple[date, dict[str, dict]]:
    """Contratos em aberto por ativo (WIN, WDO, IND, DOL...).

    Esta tabela NAO separa por tipo de participante - so por contrato. E o
    que existe de publico hoje; a divisao por participante nao esta aqui.
    """
    t = tabela("AnalyticalFramework2", dia)["table"]
    c_data = _coluna(t, "data de referencia")
    c_mercado = _coluna(t, "mercado")
    c_ativo = _coluna(t, "ativo")
    c_aberto = _coluna(t, "contratos em aberto")

    referencia = dia
    por_ativo: dict[str, dict] = {}
    for linha in t.get("values") or []:
        try:
            ativo = str(linha[c_ativo])
            descricao = str(linha[c_mercado])
            aberto = int(linha[c_aberto])
            referencia = datetime.fromisoformat(str(linha[c_data])).date()
        except (IndexError, TypeError, ValueError):
            continue
        # Um ativo aparece varias vezes (futuro, opcao de compra, de venda).
        # So o futuro interessa para o painel.
        if "futuro" not in descricao.lower() or "opção" in descricao.lower():
            continue
        por_ativo[ativo] = {"descricao": descricao, "contratos": aberto}

    if not por_ativo:
        raise comum.FonteIndisponivel(f"quadro analítico de {dia}: nenhum futuro na tabela")
    return referencia, por_ativo
