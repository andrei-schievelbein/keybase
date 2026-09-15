"""Area de leitura: a tela de terminal desenhada num QTextBrowser.

A tela e repintada por completo a cada comando - o modelo e "limpar e
reescrever N linhas". A escrita e por QTextCursor com QTextCharFormat, nao por
setHtml(): o ViewerScreen escreve cabecalho, DEPOIS o markdown, DEPOIS o
rodape, tudo no mesmo widget, e setHtml substituiria o documento inteiro a cada
chamada.

Armadilha que isso resolve: `spacing1`/`spacing3` das tags do Tk sao formato de
BLOCO. Inserir "texto\\n" com um block format ativo faz o bloco seguinte herdar
o espacamento, e a linha de baixo ganha margem sem querer. Por isso cada linha
termina com insertBlock(formato_padrao), que quebra E reseta.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import (QColor, QTextBlockFormat, QTextCharFormat,
                           QTextCursor, QTextOption)
from PySide6.QtWidgets import QTextBrowser

from .theme import ESPACAMENTO, cores_interface


class AreaTerminal(QTextBrowser):
    """QTextBrowser somente leitura com uma tabela de tags de cor."""

    def __init__(self, fonte, tema, parent=None):
        super().__init__(parent)
        self.tema = tema
        self.setFont(fonte)
        self.document().setDefaultFont(fonte)
        self.document().setUndoRedoEnabled(False)  # documento descartavel

        self.setReadOnly(True)
        # Selecionar e copiar sim; cursor piscando, nao.
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse
                                     | Qt.TextInteractionFlag.TextSelectableByKeyboard)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)  # Tab nao rouba o foco da entrada
        self.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)

        # A largura do viewport precisa ser INDEPENDENTE do conteudo, senao a
        # barra aparecendo encolhe o viewport, muda colunas() e dispara outra
        # repintura: laco. Barra sempre visivel mata isso na origem.
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.setOpenLinks(False)  # quem decide o que fazer com link e a tela

        self._formatos = {}
        self._blocos = {}
        self._bloco_padrao = QTextBlockFormat()
        self.recarregar_cores(tema)

    def recarregar_cores(self, tema):
        """(Re)constroi os formatos. Cacheados: criar por trecho e desperdicio."""
        self.tema = tema
        cores = cores_interface(tema)

        self._formatos = {}
        for tag, cor in cores.items():
            formato = QTextCharFormat()
            formato.setForeground(QColor(cor))
            self._formatos[tag] = formato

        self._blocos = {}
        for tag, (acima, abaixo) in ESPACAMENTO.items():
            bloco = QTextBlockFormat()
            bloco.setTopMargin(acima)
            bloco.setBottomMargin(abaixo)
            self._blocos[tag] = bloco

    def formato(self, tag):
        return self._formatos.get(tag)

    def cursor_no_fim(self):
        cursor = QTextCursor(self.document())
        cursor.movePosition(QTextCursor.MoveOperation.End)
        return cursor

    def escrever(self, partes, tag_bloco=None):
        """Escreve uma linha composta de (texto, tag) e quebra no fim."""
        cursor = self.cursor_no_fim()

        # Se o bloco atual ja tem conteudo, abre um novo ANTES de escrever. E o
        # que acontece depois de inserir_html(): o insertHtml deixa o cursor
        # dentro do ultimo bloco do HTML, e sem isto a proxima linha (a barra de
        # '=', por exemplo) era anexada aquele bloco e herdava a fonte dele -
        # uma barra em tamanho de cabecalho, estourando a largura.
        if not cursor.block().text() == '':
            cursor.insertBlock(self._bloco_padrao, QTextCharFormat())

        cursor.setBlockFormat(self._blocos.get(tag_bloco, self._bloco_padrao))
        for texto, tag in partes:
            formato = self._formatos.get(tag) if tag else QTextCharFormat()
            cursor.insertText(texto, formato or QTextCharFormat())
        # insertBlock com o formato padrao: quebra E reseta o espacamento, para
        # a linha seguinte nao herdar as margens desta
        cursor.insertBlock(self._bloco_padrao, QTextCharFormat())

    def inserir_html(self, html):
        self.cursor_no_fim().insertHtml(html)
