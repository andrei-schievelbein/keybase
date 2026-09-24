"""Modelos de nota: notas comuns numa pasta da raiz (padrao "Modelos"). Sem Qt.

Nao ha formato novo: um modelo e uma nota como outra qualquer, editada com E.
Ao criar uma nota com N, os modelos sao oferecidos, e {nome} e {data} no texto
do modelo sao preenchidos. str.replace, e nao str.format: modelo de codigo
cheio de chaves ({ "a": 1 }) nao pode quebrar.
"""

from datetime import date

from .model import File, Folder
from .tree import filhos_ordenados, normalizar


def pasta_de_modelos(raiz, nome):
    """A pasta de modelos, na raiz, pelo nome (sem caixa e acento), ou None."""
    if not nome:
        return None
    alvo = normalizar(nome)
    for filho in raiz.filhos or ():
        if isinstance(filho, Folder) and normalizar(filho.nome) == alvo:
            return None if filho.trancada else filho
    return None


def modelos(raiz, nome):
    """Notas da pasta de modelos com o texto disponivel (trancadas ficam de fora)."""
    pasta = pasta_de_modelos(raiz, nome)
    if pasta is None:
        return []
    return [n for n in filhos_ordenados(pasta)
            if isinstance(n, File) and n.conteudo is not None]


def preencher(texto, nome, hoje=None):
    hoje = hoje or date.today()
    return (texto.replace("{nome}", nome)
                 .replace("{data}", hoje.strftime("%d/%m/%Y")))
