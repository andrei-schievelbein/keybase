"""TerminalView: a fachada que as telas consomem.

Mantem exatamente o mesmo contrato da versao CustomTkinter - 15 metodos - para
que as ~1400 linhas de logica de apresentacao (app.py, layout.py, screens/*)
atravessem o port sem alteracao.

Tres metodos sao novos, e fecham os unicos vazamentos de widget cru que
existiam: `focar_editor`, `focar_entrada` e os de modo de edicao.

Layout:
    entrada      QLineEdit     sempre visivel, 1 linha, unico input curto
    botao_ajuda  QToolButton   quadrado, a direita da entrada, na mesma linha
    ajuda        QLabel        barra de dica, visivel sob demanda
    pilha     QStackedWidget
      0       AreaTerminal     leitura (tela de terminal e markdown do viewer)
      1       PainelNota       edicao: editar / preview / dividido
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QLineEdit, QStackedWidget,
                               QToolButton, QVBoxLayout, QWidget)

from . import fonte as mod_fonte
from .painel_nota import EDITAR, PainelNota
from .render import RenderizadorMarkdown
from .terminal import AreaTerminal
from .theme import cores_interface

LARGURA_MINIMA = 40
LARGURA_MAXIMA = 200

IDX_LEITURA = 0
IDX_EDICAO = 1


class TerminalView(QWidget):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.tema = config['theme']
        self.cores_ui = cores_interface(self.tema)

        self._criar_fontes()
        self._criar_widgets()
        self.modo_leitura()

    # --- construcao --------------------------------------------------------

    def _criar_fontes(self):
        fontes = self.config['fonts']
        self.familia = mod_fonte.escolher_familia(fontes, fontes['output_size'])
        self.fonte_entrada = mod_fonte.criar_fonte(self.familia, fontes['input_size'])
        self.fonte_saida = mod_fonte.criar_fonte(self.familia, fontes['output_size'])
        self.fonte_ajuda = mod_fonte.criar_fonte(self.familia, fontes['help_size'])
        self._largura_char = mod_fonte.largura_caractere(self.fonte_saida)

    def _criar_widgets(self):
        self.entrada = QLineEdit()
        self.entrada.setObjectName('entrada')
        self.entrada.setFont(self.fonte_entrada)

        self.botao_ajuda = QToolButton()
        self.botao_ajuda.setObjectName('botao_ajuda')
        self.botao_ajuda.setText('?')
        self.botao_ajuda.setFont(self.fonte_entrada)
        # NoFocus: clicar no botao nao pode tirar o cursor da barra
        self.botao_ajuda.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.botao_ajuda.setCursor(Qt.CursorShape.PointingHandCursor)
        self.botao_ajuda.setToolTip("Como ver a ajuda")

        self.ajuda = QLabel()
        self.ajuda.setObjectName('ajuda')
        self.ajuda.setFont(self.fonte_ajuda)
        # PlainText obrigatorio: o texto de ajuda contem ``` e o auto-detect de
        # rich text do QLabel reinterpretaria isso
        self.ajuda.setTextFormat(Qt.TextFormat.PlainText)
        self.ajuda.setWordWrap(True)
        self.ajuda.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.ajuda.setMinimumHeight(self.config['interface']['help_area_height'])
        self.ajuda.setVisible(False)

        self.out = AreaTerminal(self.fonte_saida, self.tema)
        self.out.setObjectName('saida')

        self.painel = PainelNota(self.fonte_saida, self.tema, self.config['fonts'])
        self.painel.setObjectName('painel')

        self.pilha = QStackedWidget()
        self.pilha.addWidget(self.out)      # IDX_LEITURA
        self.pilha.addWidget(self.painel)   # IDX_EDICAO

        linha_entrada = QHBoxLayout()
        linha_entrada.setContentsMargins(0, 0, 0, 0)
        linha_entrada.setSpacing(5)
        linha_entrada.addWidget(self.entrada, 1)
        linha_entrada.addWidget(self.botao_ajuda)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        layout.addLayout(linha_entrada)
        layout.addWidget(self.ajuda)
        layout.addWidget(self.pilha, 1)

        self._render = RenderizadorMarkdown(self.tema, self.config['fonts'])
        self.out.document().setDefaultStyleSheet(self._render.folha_de_estilo())

    def showEvent(self, evento):
        """Deixa o botao '?' quadrado, no mesmo lado que a altura da barra.

        So aqui, e nao em _criar_widgets: a altura da barra so e definitiva
        depois do polish do stylesheet, que a janela aplica DEPOIS de construir
        a view.
        """
        super().showEvent(evento)
        lado = max(24, self.entrada.sizeHint().height())
        self.botao_ajuda.setFixedSize(lado, lado)

    # --- medida ------------------------------------------------------------

    def colunas(self):
        """Quantos caracteres cabem na largura atual da area de leitura."""
        largura_px = self.out.viewport().width()
        if largura_px <= 1:  # ainda nao mostrado
            largura_px = self._largura_presumida()
        margem = 2 * self.out.document().documentMargin()
        colunas = int((largura_px - margem - 2) // self._largura_char)
        return max(LARGURA_MINIMA, min(LARGURA_MAXIMA, colunas))

    def _largura_presumida(self):
        try:
            return int(self.config['geometry'].split('x')[0]) - 40
        except (ValueError, IndexError, KeyError):
            return 760

    # --- modos -------------------------------------------------------------

    def modo_leitura(self):
        """Tela de terminal em tela cheia. Esconde o painel de edicao inteiro."""
        self.pilha.setCurrentIndex(IDX_LEITURA)
        self.entrada.setEnabled(True)
        self.entrada.setFocus()

    def modo_edicao(self, texto, modo=None):
        self.pilha.setCurrentIndex(IDX_EDICAO)
        self.painel.carregar(texto, modo or EDITAR)

    def texto_editor(self):
        """Conteudo cru do editor, sem nenhum tratamento de sentinela."""
        return self.painel.texto()

    def definir_modo_edicao(self, modo):
        self.painel.definir_modo(modo)

    def ciclar_modo_edicao(self):
        return self.painel.ciclar()

    def modo_edicao_atual(self):
        return self.painel.modo()

    def em_edicao(self):
        return self.pilha.currentIndex() == IDX_EDICAO

    # --- escrita na area de leitura ---------------------------------------

    def limpar(self):
        self.out.clear()

    def linha(self, texto="", tag=None):
        self.out.escrever([(texto, tag)], tag_bloco=tag)

    def trechos(self, partes):
        """Escreve uma linha composta de (texto, tag) e quebra no fim."""
        tag_bloco = partes[0][1] if partes else None
        self.out.escrever(partes, tag_bloco=tag_bloco)

    def barra(self, largura=None):
        """Barra de '=' delimitando um bloco, no estilo da versao 1."""
        from .layout import barra
        self.linha(barra(largura or self.colunas()), 'separador')

    #: mantido como apelido para nao espalhar a troca de nome pelas telas
    separador = barra

    def cabecalho(self, texto, tag='breadcrumb'):
        """Bloco de topo: barra, titulo, barra."""
        self.barra()
        self.linha(" " + texto, tag)
        self.barra()

    def markdown(self, texto):
        """Insere o markdown renderizado no fim da area de leitura.

        insertHtml e nao setHtml: o viewer escreve cabecalho antes e rodape
        depois, no mesmo documento.
        """
        self.out.inserir_html(self._render.html(texto))

    def ao_topo(self):
        self.out.moveCursor(QTextCursor.MoveOperation.Start)
        self.out.verticalScrollBar().setValue(0)

    # --- botao de ajuda ----------------------------------------------------

    def habilitar_ajuda(self, ativo):
        """Apaga o botao onde o menu nao existe, para o clique nao ser inerte."""
        self.botao_ajuda.setEnabled(bool(ativo))

    # --- barra de ajuda ----------------------------------------------------

    def dica(self, texto):
        """Mostra a barra de ajuda; None ou vazio a esconde."""
        if not texto:
            self.ajuda.clear()
            self.ajuda.setVisible(False)
            return
        self.ajuda.setText(texto)
        self.ajuda.setVisible(True)

    # --- campo de entrada --------------------------------------------------

    def ler_entrada(self):
        return self.entrada.text().strip()

    def limpar_entrada(self):
        self.entrada.clear()

    def preencher_entrada(self, valor):
        """Pre-preenche o campo (renomear vem com o nome atual)."""
        self.entrada.setText(valor or '')
        self.entrada.setFocus()

    # --- foco (fecha os vazamentos de widget cru) --------------------------

    def focar_entrada(self):
        self.entrada.setFocus()

    def focar_editor(self):
        self.painel.editor.setFocus()
