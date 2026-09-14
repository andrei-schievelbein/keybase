"""Primitivas de desenho do terminal: barras, breadcrumb, itens e menu.

Estilo visual herdado da versao 1: blocos delimitados por barras de '=' e
linhas no formato "N - Rotulo", densas e alinhadas. Tudo em ASCII (mais '…'):
fontes monoespacadas comuns nao garantem glifo para emoji num widget Text, que
acabaria desenhando caixas.

Pasta = nome com '/' no fim e contagem entre colchetes; nota = nome puro.

Toda largura vem de TerminalView.colunas(), calculada da largura real do widget
e da largura de um caractere na fonte - nao de uma constante. Alinhar por
contagem de caracteres so funciona com fonte monoespacada, e a escolha da
familia e feita em view._escolher_familia().
"""

from ..model import Folder
from ..tree import contar_itens

LARGURA_PADRAO = 78
MARCA_RAIZ = "~"
CARACTERE_BARRA = "="
LARGURA_NUMERO = 2
LARGURA_LETRA = 4  # cabe 'sair' alinhado com as letras isoladas


def barra(largura=LARGURA_PADRAO):
    return CARACTERE_BARRA * largura


def montar_breadcrumb(cadeia, largura=LARGURA_PADRAO):
    """Caminho legivel, colapsando o meio quando nao cabe.

    Mantem sempre a raiz e os dois ultimos niveis: ~ / Python / … / ORM / Qu...
    """
    nomes = [no.nome for no in cadeia[1:]]
    if not nomes:
        return MARCA_RAIZ

    partes = [MARCA_RAIZ] + nomes
    texto = " / ".join(partes)
    if len(texto) <= largura:
        return texto

    while len(partes) > 3:
        partes = [MARCA_RAIZ, "…"] + partes[-2:]
        texto = " / ".join(partes)
        if len(texto) <= largura:
            return texto
        break

    if len(texto) > largura:
        texto = texto[:max(1, largura - 1)] + "…"
    return texto


def linha_item(numero, no, largura=LARGURA_PADRAO):
    """Partes (texto, tag) de uma linha da listagem, no formato 'N - Nome'."""
    prefixo = f"{numero:>{LARGURA_NUMERO}} - "
    partes = [(prefixo, 'numero')]

    if isinstance(no, Folder):
        contador = f"[{contar_itens(no)}]" if no.filhos else ""
        espaco_nome = largura - len(prefixo) - len(contador) - 2
        nome = truncar(no.nome + "/", espaco_nome)
        partes.append((nome, 'pasta'))
        if contador:
            preenchimento = largura - len(prefixo) - len(nome) - len(contador)
            partes.append((" " * max(2, preenchimento), None))
            partes.append((contador, 'contador'))
    else:
        partes.append((truncar(no.nome, largura - len(prefixo)), 'nota'))

    return partes


def linha_resultado(numero, resultado, largura=LARGURA_PADRAO):
    """Duas ou tres linhas por hit de busca: rotulo+nome, caminho e trecho."""
    prefixo = f"{numero:>{LARGURA_NUMERO}} - "
    rotulo = f"[{resultado.rotulo_tipo}] "
    recuo = " " * (len(prefixo) + len(rotulo))

    linhas = [[
        (prefixo, 'numero'),
        (rotulo, 'contador'),
        (truncar(resultado.no.nome, largura - len(prefixo) - len(rotulo)),
         'pasta' if resultado.e_pasta else 'nota'),
    ]]
    linhas.append([(recuo, None),
                   (truncar(resultado.caminho, largura - len(recuo)), 'contador')])
    if resultado.trecho:
        linhas.append([(recuo, None),
                       (truncar(resultado.trecho, largura - len(recuo)), 'dica')])
    return linhas


def celula_comando(letra, rotulo):
    """'   C - Nova pasta' — a letra alinhada a direita para 'sair' encaixar."""
    return f"{letra:>{LARGURA_LETRA}} - {rotulo}"


def montar_menu(comandos, rotulos, disponiveis, largura=LARGURA_PADRAO, extras=()):
    """Menu em duas colunas, no formato da versao 1.

    Sai do mesmo dict que despacha os comandos, entao menu e comportamento nao
    podem divergir - na versao anterior divergiam.
    """
    itens = [(letra, rotulos[letra])
             for letra in comandos
             if letra in disponiveis and letra in rotulos]
    itens += [par for par in extras]
    if not itens:
        return []

    metade = (len(itens) + 1) // 2
    esquerda, direita = itens[:metade], itens[metade:]
    coluna = max(len(celula_comando(l, r)) for l, r in esquerda) + 4
    coluna = min(coluna, max(20, largura // 2))

    linhas = []
    for i, (letra, rotulo) in enumerate(esquerda):
        texto = celula_comando(letra, rotulo).ljust(coluna)
        if i < len(direita):
            texto += celula_comando(*direita[i])
        linhas.append(truncar(texto.rstrip(), largura))
    return linhas


def truncar(texto, largura):
    if largura < 4:
        return texto[:max(0, largura)]
    if len(texto) <= largura:
        return texto
    return texto[:largura - 1] + "…"
