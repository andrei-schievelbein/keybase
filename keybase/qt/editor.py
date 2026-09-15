"""Editor de Markdown cru.

QPlainTextEdit e nao QTextEdit, e o motivo principal nao e desempenho: o
QTextEdit aceita rich text na colagem, e colar de um navegador injeta
formatacao no documento. O QPlainTextEdit simplesmente NAO TEM esse modo - o
widget nao pode transformar o conteudo do usuario.

Dado o historico (uma nota terminada na palavra CTRL_S era truncada ao salvar),
a regra aqui e dura: o editor nunca altera o texto do usuario. `texto()` e
toPlainText() puro, sem nenhum tratamento.
"""

import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetricsF, QTextCursor
from PySide6.QtWidgets import QPlainTextEdit

from .realce import RealceMarkdown

LARGURA_TAB = 4

RE_LISTA_ITEM = re.compile(r'^(\s*)([-*+]|\d{1,9}[.)])(\s+)(\[[ xX]\]\s+)?(.*)$')


class EditorMarkdown(QPlainTextEdit):
    def __init__(self, fonte, tema, parent=None):
        super().__init__(parent)
        self.setFont(fonte)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.setTabStopDistance(LARGURA_TAB * QFontMetricsF(fonte).horizontalAdvance(' '))
        self.setUndoRedoEnabled(True)
        self.document().setDocumentMargin(8)
        self.realce = RealceMarkdown(self.document(), tema, fonte.family())

    def texto(self):
        """Conteudo cru, sem nenhum tratamento. Ver docstring do modulo."""
        return self.toPlainText()

    def definir_texto(self, texto):
        self.setPlainText(texto)
        self.document().clearUndoRedoStacks()
        self.moveCursor(QTextCursor.MoveOperation.Start)

    def recarregar_cores(self, tema):
        self.realce.recarregar_cores(tema)

    # --- comportamentos de edicao -----------------------------------------

    def keyPressEvent(self, evento):
        tecla = evento.key()

        if tecla == Qt.Key.Key_Tab and not evento.modifiers():
            if self.textCursor().hasSelection():
                self._indentar(1)
                return
            self.insertPlainText(' ' * LARGURA_TAB)
            return

        if tecla == Qt.Key.Key_Backtab or (
                tecla == Qt.Key.Key_Tab
                and evento.modifiers() == Qt.KeyboardModifier.ShiftModifier):
            self._indentar(-1)
            return

        if tecla in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not evento.modifiers():
            if self._continuar_lista():
                return

        super().keyPressEvent(evento)

    def _indentar(self, direcao):
        """Indenta ou desindenta as linhas da selecao."""
        cursor = self.textCursor()
        inicio, fim = cursor.selectionStart(), cursor.selectionEnd()

        cursor.beginEditBlock()
        cursor.setPosition(inicio)
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        while cursor.position() <= fim:
            cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            if direcao > 0:
                cursor.insertText(' ' * LARGURA_TAB)
                fim += LARGURA_TAB
            else:
                linha = cursor.block().text()
                remover = len(linha) - len(linha.lstrip(' '))
                remover = min(remover, LARGURA_TAB)
                for _ in range(remover):
                    cursor.deleteChar()
                fim -= remover
            if not cursor.movePosition(QTextCursor.MoveOperation.NextBlock):
                break
        cursor.endEditBlock()

    def _continuar_lista(self):
        """Enter dentro de lista repete o marcador; numera sozinho.

        Se a linha e SO o marcador, limpa a linha - e como se encerra a lista.
        """
        cursor = self.textCursor()
        if cursor.hasSelection():
            return False

        linha = cursor.block().text()
        casamento = RE_LISTA_ITEM.match(linha)
        if not casamento:
            return False

        recuo, marcador, espaco, tarefa, conteudo = casamento.groups()

        if not conteudo.strip():
            # lista vazia: encerra
            cursor.beginEditBlock()
            cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock,
                                QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
            cursor.insertText('\n')
            cursor.endEditBlock()
            return True

        proximo = marcador
        numero = re.match(r'^(\d{1,9})([.)])$', marcador)
        if numero:
            proximo = f'{int(numero.group(1)) + 1}{numero.group(2)}'

        prefixo_tarefa = '[ ] ' if tarefa else ''
        cursor.insertText(f'\n{recuo}{proximo}{espaco}{prefixo_tarefa}')
        return True
