"""Blocos de codigo cercados (``` ou ~~~) de uma nota Markdown. Sem Qt.

E o que o Y2 copia: o segundo bloco, na ordem em que aparece no texto. As
regras de cerca seguem o CommonMark no que importa aqui: ate 3 espacos de
recuo, 3+ crases ou tis, e o fechamento com o mesmo caractere e pelo menos o
mesmo comprimento. Cerca aberta ate o fim da nota tambem conta como bloco -
o preview a mostra assim, entao a numeracao tem de bater.
"""

import re
from dataclasses import dataclass

_ABERTURA = re.compile(r'^( {0,3})(`{3,}|~{3,})\s*([^`\s]*)')


@dataclass(frozen=True)
class Bloco:
    linguagem: str
    texto: str

    @property
    def n_linhas(self):
        return len(self.texto.splitlines()) if self.texto else 0

    def rotulo(self, largura=50):
        """'python (3 linhas): df = pd.read_csv(...)' para a lista do Y."""
        nome = self.linguagem or "texto"
        plural = "linha" if self.n_linhas == 1 else "linhas"
        primeira = next((l.strip() for l in self.texto.splitlines() if l.strip()), "")
        rotulo = f"{nome} ({self.n_linhas} {plural})"
        if primeira:
            rotulo += f": {primeira}"
        return rotulo if len(rotulo) <= largura else rotulo[:largura - 1] + "…"


def blocos_de_codigo(markdown):
    """Lista de Bloco, na ordem do texto."""
    blocos = []
    linhas = (markdown or "").splitlines()
    i = 0
    while i < len(linhas):
        abertura = _ABERTURA.match(linhas[i])
        if not abertura:
            i += 1
            continue
        recuo, cerca, linguagem = abertura.groups()
        fechamento = re.compile(rf'^ {{0,3}}{re.escape(cerca[0])}{{{len(cerca)},}}\s*$')
        corpo = []
        i += 1
        while i < len(linhas) and not fechamento.match(linhas[i]):
            linha = linhas[i]
            # o recuo da cerca sai de cada linha do corpo, como no CommonMark
            corpo.append(linha[len(recuo):] if linha.startswith(recuo) else linha.lstrip(' '))
            i += 1
        blocos.append(Bloco(linguagem, "\n".join(corpo)))
        i += 1  # pula o fechamento
    return blocos
