"""Le planilhas que VOCE baixou a mao, sem instalar nada.

Isto existe porque a B3 proibe coleta automatizada do site dela. Entao o
robo nunca acessa b3.com.br: ele so le arquivos que ja estao no seu
computador, dentro da pasta `b3-manual`.

Formatos aceitos:

  .csv  .txt   texto separado por ponto-e-virgula, virgula ou tabulacao
  .xlsx .xlsm  planilha do Excel moderna

O .xlsx e um ZIP com XML dentro. Python sabe abrir ZIP e ler XML sem
biblioteca nenhuma, e so isso que fazemos aqui - nada de openpyxl nem
pandas, para o projeto continuar rodando num computador limpo.

O .xls antigo (binario, de antes de 2007) NAO da para ler assim. Se o
arquivo for desses, abra no Excel e salve como .xlsx ou .csv.
"""

from __future__ import annotations

import csv
import io
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

# Uma linha de planilha, cada celula como texto. Celula vazia vira "".
Linha = list[str]


class PlanilhaIlegivel(Exception):
    """O arquivo existe, mas nao deu para ler. A mensagem diz o porque."""


def ler_planilha(caminho: Path) -> list[Linha]:
    """Devolve a planilha como lista de linhas de texto."""
    sufixo = caminho.suffix.lower()
    if sufixo in (".csv", ".txt"):
        return _ler_texto(caminho)
    if sufixo in (".xlsx", ".xlsm"):
        return _ler_xlsx(caminho)
    if sufixo == ".xls":
        raise PlanilhaIlegivel(
            f"{caminho.name} esta no formato .xls antigo. Abra no Excel e salve "
            "como .xlsx ou .csv, depois rode de novo."
        )
    raise PlanilhaIlegivel(f"{caminho.name}: nao sei ler arquivo {sufixo}")


def _ler_texto(caminho: Path) -> list[Linha]:
    """CSV ou TXT. Descobre sozinho o separador e a acentuacao.

    Arquivo da B3 costuma vir em latin-1 e com ponto-e-virgula; arquivo
    salvo pelo Excel brasileiro, igual. Mas nao custa aceitar os outros.
    """
    bruto = caminho.read_bytes()
    texto = None
    for codificacao in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            texto = bruto.decode(codificacao)
            break
        except UnicodeDecodeError:
            continue
    if texto is None:  # latin-1 aceita qualquer byte, entao nao chega aqui
        raise PlanilhaIlegivel(f"{caminho.name}: acentuacao desconhecida")

    amostra = texto[:8000]
    separador = max(";,\t", key=amostra.count)
    leitor = csv.reader(io.StringIO(texto), delimiter=separador)
    return [[(c or "").strip() for c in linha] for linha in leitor]


def _ler_xlsx(caminho: Path) -> list[Linha]:
    """Primeira aba de um .xlsx, como texto.

    Datas vem como numero de serie do Excel e sao convertidas; o resto
    fica como esta no arquivo, e quem interpreta e o `numero()` abaixo.
    """
    try:
        with zipfile.ZipFile(caminho) as pacote:
            textos = _textos_compartilhados(pacote)
            nome_aba = _primeira_aba(pacote)
            with pacote.open(nome_aba) as aba:
                return _linhas_da_aba(aba, textos)
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError) as erro:
        raise PlanilhaIlegivel(f"{caminho.name}: planilha corrompida ou estranha ({erro})") from erro


def _textos_compartilhados(pacote: zipfile.ZipFile) -> list[str]:
    """O Excel guarda todo texto repetido numa tabela unica; as celulas
    apontam para ela por numero. Sem isto, celula de texto vira indice."""
    if "xl/sharedStrings.xml" not in pacote.namelist():
        return []
    raiz = ElementTree.fromstring(pacote.read("xl/sharedStrings.xml"))
    saida = []
    for item in raiz.findall(f"{NS}si"):
        # Texto formatado vem picado em varios <t>; junta tudo.
        saida.append("".join(pedaco.text or "" for pedaco in item.iter(f"{NS}t")))
    return saida


def _primeira_aba(pacote: zipfile.ZipFile) -> str:
    nomes = sorted(n for n in pacote.namelist() if n.startswith("xl/worksheets/sheet"))
    if not nomes:
        raise PlanilhaIlegivel("a planilha nao tem nenhuma aba")
    return nomes[0]


def _linhas_da_aba(aba, textos: list[str]) -> list[Linha]:
    linhas: list[Linha] = []
    for _, elemento in ElementTree.iterparse(aba, events=("end",)):
        if elemento.tag != f"{NS}row":
            continue
        celulas: dict[int, str] = {}
        for celula in elemento.findall(f"{NS}c"):
            coluna = _coluna(celula.get("r") or "")
            celulas[coluna] = _valor(celula, textos)
        largura = max(celulas) + 1 if celulas else 0
        linhas.append([celulas.get(i, "") for i in range(largura)])
        elemento.clear()  # planilha da B3 e grande; nao guarda o XML inteiro
    return linhas


def _coluna(referencia: str) -> int:
    """"C7" -> 2. A coluna vem como letra e as celulas vazias nao aparecem
    no arquivo, por isso precisamos da posicao exata de cada uma."""
    letras = "".join(c for c in referencia if c.isalpha()).upper()
    indice = 0
    for letra in letras:
        indice = indice * 26 + (ord(letra) - 64)
    return max(indice - 1, 0)


def _valor(celula, textos: list[str]) -> str:
    tipo = celula.get("t")
    if tipo == "inlineStr":
        return "".join(p.text or "" for p in celula.iter(f"{NS}t")).strip()
    bruto = celula.find(f"{NS}v")
    if bruto is None or bruto.text is None:
        return ""
    texto = bruto.text.strip()
    if tipo == "s":  # indice na tabela de textos
        try:
            return textos[int(texto)]
        except (ValueError, IndexError):
            return ""
    return texto


_SO_NUMERO = re.compile(r"[^0-9,.\-]")


def numero(bruto: str) -> float | None:
    """Converte texto de planilha em numero, no padrao brasileiro.

    Aceita 1.234.567,89 / 1234567,89 / -1.234,5 / (1.234,5) / 1234567.89
    e devolve None quando a celula nao e numero (titulo, data, "-", vazio).

    Parenteses valem negativo: planilha de contabilidade usa isso.
    """
    if bruto is None:
        return None
    texto = str(bruto).strip()
    if not texto:
        return None

    negativo = texto.startswith("(") and texto.endswith(")")
    texto = _SO_NUMERO.sub("", texto)
    if texto in ("", "-", ".", ",", "-."):
        return None

    if "," in texto:
        # Virgula presente: ela e a decimal e o ponto e separador de milhar.
        texto = texto.replace(".", "").replace(",", ".")
    elif texto.count(".") > 1:
        # 1.234.567 sem virgula: pontos sao milhar, nao decimal.
        texto = texto.replace(".", "")
    elif re.fullmatch(r"-?\d{1,3}\.\d{3}", texto):
        # Caso ambiguo, e importante: "-42.310".
        #
        # Em texto brasileiro isso e quarenta e dois mil trezentos e dez. Para
        # ser quarenta e dois inteiros e trinta e um, o arquivo escreveria
        # "-42,31" - a decimal aqui e virgula, sempre.
        #
        # Ler isto como -42,31 ja aconteceu: o saldo de contratos do
        # estrangeiro apareceu como 42 em vez de 42.310, mil vezes menor.
        texto = texto.replace(".", "")

    try:
        valor = float(texto)
    except ValueError:
        return None
    return -valor if negativo else valor


def sem_acento(texto: str) -> str:
    """Para comparar titulos de coluna sem depender de acento nem de
    maiuscula: "Investidor Não Residente" e "investidor nao residente"
    precisam casar."""
    import unicodedata

    normalizado = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in normalizado if not unicodedata.combining(c)).lower().strip()
