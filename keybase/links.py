"""Links entre notas: [[Nome]], [[Pasta/Nome]] e [[alvo|texto mostrado]]. Sem Qt.

A resolucao e por nome, ignorando caixa e acento (como a busca):
- com '/', e um caminho a partir da raiz: pastas pelo nome, e o ultimo pedaco
  e a nota;
- sem '/', e qualquer nota com esse nome. Mais de uma: quem chama pergunta.

So enxerga o que esta visivel: nota dentro de pasta cifrada trancada nao
resolve ate a pasta abrir - o link aparece como quebrado, nao como vazamento.
"""

import re

from .model import File, Folder
from .tree import normalizar, percorrer

#: [[alvo]] ou [[alvo|texto]] - sem colchete nem quebra de linha dentro
RE_LINK = re.compile(r'\[\[([^\[\]\n|]+?)(?:\|([^\[\]\n]+?))?\]\]')


def separar(conteudo):
    """'alvo|texto' -> (alvo, texto mostrado)."""
    alvo, _, texto = conteudo.partition('|')
    return alvo.strip(), (texto.strip() or alvo.strip())


def resolver(raiz, alvo):
    """Notas que o alvo aponta (lista, possivelmente vazia ou com varias)."""
    alvo = (alvo or "").strip().strip('/')
    if not alvo:
        return []
    if '/' in alvo:
        return _por_caminho(raiz, [p.strip() for p in alvo.split('/') if p.strip()])
    nome = normalizar(alvo)
    return [no for no, _ in percorrer(raiz)
            if isinstance(no, File) and normalizar(no.nome) == nome]


def _por_caminho(raiz, partes):
    atual = [raiz]
    for i, parte in enumerate(partes):
        ultimo = i == len(partes) - 1
        proximos = []
        for pasta in atual:
            for filho in pasta.filhos or ():
                if normalizar(filho.nome) != normalizar(parte):
                    continue
                if ultimo and isinstance(filho, File):
                    proximos.append(filho)
                elif not ultimo and isinstance(filho, Folder):
                    proximos.append(filho)
        atual = proximos
    return atual
