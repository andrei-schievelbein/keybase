"""Primitivas de desenho do terminal: breadcrumb, linhas de item e rodape.

Convencao visual 100% ASCII (mais '─' e '…'): Consolas e Courier New no Windows
nao garantem glifo para emoji num widget Text, que acabaria desenhando caixas.
Pasta = nome com '/' no fim e contagem entre colchetes; nota = nome puro.
"""

from ..model import Folder
from ..tree import contar_itens

LARGURA = 78
MARCA_RAIZ = "~"


def montar_breadcrumb(cadeia, largura=LARGURA):
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
        # ja colapsado ao minimo; trunca o ultimo segmento
        break

    if len(texto) > largura:
        texto = texto[:largura - 1] + "…"
    return texto


def linha_item(numero, no, largura=LARGURA):
    """Partes (texto, tag) de uma linha da listagem."""
    prefixo = f"  {numero:>2}  "
    partes = [(prefixo, 'numero')]

    if isinstance(no, Folder):
        nome = no.nome + "/"
        partes.append((nome, 'pasta'))
        total = contar_itens(no)
        if total:
            contador = f"[{total}]"
            espaco = largura - len(prefixo) - len(nome) - len(contador)
            partes.append((" " * max(2, espaco), None))
            partes.append((contador, 'contador'))
    else:
        partes.append((no.nome, 'nota'))

    return partes


def linha_resultado(numero, resultado):
    """Duas ou tres linhas por hit de busca: rotulo+nome, caminho e trecho."""
    linhas = [[
        (f"  {numero:>2}  ", 'numero'),
        (f"[{resultado.rotulo_tipo}]  ", 'contador'),
        (resultado.no.nome, 'pasta' if resultado.e_pasta else 'nota'),
    ]]
    linhas.append([("      " + " " * 8, None), (resultado.caminho, 'contador')])
    if resultado.trecho:
        linhas.append([("      " + " " * 8, None), (resultado.trecho, 'dica')])
    return linhas


def montar_rodape(comandos, rotulos, disponiveis, largura=LARGURA):
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
        candidato = f"{atual}   {item}" if atual else f"  {item}"
        if len(candidato) > largura:
            linhas.append(atual)
            atual = f"  {item}"
        else:
            atual = candidato
    if atual:
        linhas.append(atual)
    return linhas
