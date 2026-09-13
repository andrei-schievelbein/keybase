"""Primitivas de desenho do terminal: breadcrumb, linhas de item e rodape.

Convencao visual 100% ASCII (mais '─' e '…'): fontes monoespacadas comuns nao
garantem glifo para emoji num widget Text, que acabaria desenhando caixas.
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
RECUO = "  "
LARGURA_NUMERO = 2


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
    """Partes (texto, tag) de uma linha da listagem."""
    prefixo = f"{RECUO}{numero:>{LARGURA_NUMERO}}  "
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
    prefixo = f"{RECUO}{numero:>{LARGURA_NUMERO}}  "
    rotulo = f"[{resultado.rotulo_tipo}]  "
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


def montar_rodape(comandos, rotulos, disponiveis, largura=LARGURA_PADRAO):
    """Rodape gerado a partir do dict de comandos da tela.

    Como o texto sai do mesmo dict que o despacho usa, menu e comportamento nao
    podem divergir - na versao anterior divergiam.
    """
    itens = [f"{letra} {rotulos[letra]}"
             for letra in comandos
             if letra in disponiveis and letra in rotulos]

    linhas = []
    atual = ""
    for item in itens:
        candidato = f"{atual}   {item}" if atual else f"{RECUO}{item}"
        if len(candidato) > largura and atual:
            linhas.append(atual)
            atual = f"{RECUO}{item}"
        else:
            atual = candidato
    if atual:
        linhas.append(atual)
    return linhas


def truncar(texto, largura):
    if largura < 4:
        return texto[:max(0, largura)]
    if len(texto) <= largura:
        return texto
    return texto[:largura - 1] + "…"
