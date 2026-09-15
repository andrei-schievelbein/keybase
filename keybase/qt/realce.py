"""Realce de sintaxe do Markdown no editor.

Nao roda Pygments aqui: tokenizar a cada tecla seria caro e desnecessario, ja
que o preview mostra o codigo colorido. O conteudo cercado recebe cor e fundo
uniformes.

O ponto delicado sao as cercas, que atravessam varias linhas e exigem estado
por bloco. O estado guarda o TIPO e o TAMANHO da cerca, nao um simples 1: sem
isso, um ``` dentro de um bloco aberto com ```` fecharia o bloco cedo -
situacao real numa base de notas que documenta Markdown.
"""

import re

from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat

from .theme import cores_markdown

RE_CERCA = re.compile(r'^\s{0,3}(`{3,}|~{3,})\s*([\w+#.-]*)\s*$')
RE_TITULO = re.compile(r'^\s{0,3}(#{1,6})\s+(.*)$')
RE_CITACAO = re.compile(r'^\s{0,3}>\s?')
RE_TAREFA = re.compile(r'^(\s*)([-*+])\s+\[([ xX])\]\s')
RE_LISTA = re.compile(r'^(\s*)([-*+]|\d{1,9}[.)])\s+')
RE_REGRA = re.compile(r'^\s{0,3}([-*_])\s*(?:\1\s*){2,}$')
RE_TABELA = re.compile(r'^\s{0,3}\|.*\|\s*$')

RE_COD_INLINE = re.compile(r'(`+)(?!`)(.+?)(?<!`)\1')
RE_NEGRITO = re.compile(r'(\*\*|__)(?=\S)(.+?)(?<=\S)\1')
RE_ITALICO = re.compile(r'(?<![*_\w])([*_])(?=\S)([^*_]+?)(?<=\S)\1(?![*_\w])')
RE_RISCADO = re.compile(r'(~~)(?=\S)(.+?)(?<=\S)\1')
RE_LINK = re.compile(r'(!?\[)([^\]]*)(\]\()([^)\s]+)(?:\s+"[^"]*")?(\))')

SEM_CERCA = 0
BASE_CRASE = 1000
BASE_TIL = 2000


class RealceMarkdown(QSyntaxHighlighter):
    def __init__(self, documento, tema, familia):
        super().__init__(documento)
        self.familia = familia
        self.recarregar_cores(tema)

    def recarregar_cores(self, tema):
        c = cores_markdown(tema)

        def formato(cor=None, negrito=False, italico=False, riscado=False, fundo=None):
            f = QTextCharFormat()
            if cor:
                f.setForeground(QColor(cor))
            if fundo:
                f.setBackground(QColor(fundo))
            if negrito:
                f.setFontWeight(QFont.Weight.Bold)
            f.setFontItalic(italico)
            f.setFontStrikeOut(riscado)
            return f

        self.f_titulo = [
            formato(c['h1'], negrito=True), formato(c['h2'], negrito=True),
            formato(c['h3'], negrito=True), formato(c['h4'], negrito=True),
            formato(c['h4'], negrito=True), formato(c['h4'], negrito=True),
        ]
        self.f_negrito = formato(c['bold'], negrito=True)
        self.f_italico = formato(c['italic'], italico=True)
        self.f_riscado = formato(c['quote'], riscado=True)
        # inline fica com a cor de codigo; o conteudo cercado usa a cor normal
        # de texto, senao um bloco inteiro de laranja cansa a vista
        self.f_codigo = formato(c['code_fg'], fundo=c['code_bg'])
        self.f_bloco = formato(c['texto'], fundo=c['code_bg'])
        self.f_cerca = formato(c['quote'], fundo=c['code_bg'])
        self.f_citacao = formato(c['quote'], italico=True)
        self.f_marcador = formato(c['h2'], negrito=True)
        self.f_regra = formato(c['rule'])
        self.f_link = formato(c['link'])
        self.f_url = formato(c['quote'])
        self.f_tabela = formato(c['h3'])
        self.rehighlight()

    @staticmethod
    def _codificar(cerca):
        base = BASE_CRASE if cerca[0] == '`' else BASE_TIL
        return base + len(cerca)

    def highlightBlock(self, texto):
        estado = self.previousBlockState()

        if estado > SEM_CERCA:
            # dentro de uma cerca: fundo de codigo, cor de texto normal
            self.setFormat(0, len(texto), self.f_bloco)
            fecha = RE_CERCA.match(texto)
            if fecha and self._codificar(fecha.group(1)) == estado and not fecha.group(2):
                self.setFormat(0, len(texto), self.f_cerca)
                self.setCurrentBlockState(SEM_CERCA)
            else:
                self.setCurrentBlockState(estado)
            return

        abre = RE_CERCA.match(texto)
        if abre:
            self.setFormat(0, len(texto), self.f_cerca)
            self.setCurrentBlockState(self._codificar(abre.group(1)))
            return

        self.setCurrentBlockState(SEM_CERCA)
        if self._regras_de_bloco(texto):
            return
        self._regras_inline(texto)

    def _regras_de_bloco(self, texto):
        """True quando a linha inteira ja foi pintada."""
        if RE_REGRA.match(texto):
            self.setFormat(0, len(texto), self.f_regra)
            return True

        titulo = RE_TITULO.match(texto)
        if titulo:
            nivel = min(len(titulo.group(1)), 6) - 1
            self.setFormat(0, len(texto), self.f_titulo[nivel])
            return True

        if RE_CITACAO.match(texto):
            self.setFormat(0, len(texto), self.f_citacao)
            return True

        if RE_TABELA.match(texto):
            self.setFormat(0, len(texto), self.f_tabela)
            return True

        tarefa = RE_TAREFA.match(texto)
        if tarefa:
            self.setFormat(len(tarefa.group(1)), len(tarefa.group(0)) - len(tarefa.group(1)),
                           self.f_marcador)
            self._regras_inline(texto)
            return True

        lista = RE_LISTA.match(texto)
        if lista:
            self.setFormat(len(lista.group(1)), len(lista.group(2)), self.f_marcador)

        return False

    def _regras_inline(self, texto):
        for casamento in RE_COD_INLINE.finditer(texto):
            self.setFormat(casamento.start(), len(casamento.group(0)), self.f_codigo)
        for casamento in RE_NEGRITO.finditer(texto):
            self.setFormat(casamento.start(), len(casamento.group(0)), self.f_negrito)
        for casamento in RE_ITALICO.finditer(texto):
            self.setFormat(casamento.start(), len(casamento.group(0)), self.f_italico)
        for casamento in RE_RISCADO.finditer(texto):
            self.setFormat(casamento.start(), len(casamento.group(0)), self.f_riscado)
        for casamento in RE_LINK.finditer(texto):
            self.setFormat(casamento.start(2), len(casamento.group(2)), self.f_link)
            self.setFormat(casamento.start(4), len(casamento.group(4)), self.f_url)
