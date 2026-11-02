"""Os dez indicadores do placar de pre-mercado.

A especificacao pedia futuros de S&P e Nasdaq, minerio em Dalian e Brent.
Esses dependem de licenca das bolsas (CME, DCE, ICE), que nao se consegue
em plano barato nem para uso pessoal. Entao cada um foi trocado por um
papel negociado em Nova York que segue a mesma coisa.

A troca esta anotada em cada linha, e a tela mostra o papel de verdade -
nada de dizer "S&P 500 futuro" quando o numero e do SPY.

"inverte" marca os indicadores em que a QUEDA e que favorece a bolsa
brasileira: dolar forte e juro americano alto puxam dinheiro para fora.
"""

INDICADORES = [
    # simbolo, nome na tela, peso no WIN, inverte, o que substitui
    ("SPY", "S&P 500 (SPY)", "alto", False, "futuro do S&P 500"),
    ("QQQ", "Nasdaq 100 (QQQ)", "médio", False, "futuro do Nasdaq"),
    ("EWZ", "Brasil (EWZ)", "alto", False, None),
    ("VALE", "Vale ADR", "alto", False, None),
    ("PBR", "Petrobras ADR", "médio", False, None),
    ("ITUB", "Itaú ADR", "médio", False, None),
    ("UUP", "Dólar (UUP)", "alto", True, "DXY"),
    ("BNO", "Petróleo Brent (BNO)", "médio", False, "Brent à vista"),
    ("IEF", "Treasury 7-10a (IEF)", "alto", False, "juro do Treasury de 10 anos"),
    ("FXI", "China (FXI)", "médio", False, "minério em Dalian"),
]


def favoravel(variacao: float, inverte: bool) -> bool:
    """Este indicador esta a favor da alta do indice brasileiro?

    Nao e previsao: e a leitura do sinal de hoje, um a um.
    """
    return variacao < 0 if inverte else variacao > 0
