"""Painel de edicao de uma nota: editar, preview e dividido.

Este e o unico lugar do app em que a tela se divide. Fora da edicao de nota, o
KeyBase continua sendo o terminal de tela cheia.

Um QSplitter com UMA instancia de editor e UMA de preview; os modos sao so
visibilidade. Isso e o que garante que trocar de modo nunca perca o texto nao
salvo nem a posicao do cursor - os widgets continuam vivos. Com um
QStackedWidget seriam necessarios dois editores (e sincronizar dois documentos
e exatamente o tipo de estado duplicado que gera bug).

O preview mostra sempre o texto DO EDITOR, nunca o que esta em disco: a
pergunta que ele responde e "como vai ficar o que acabei de digitar".
"""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QSplitter, QTextBrowser, QVBoxLayout, QWidget

from .editor import EditorMarkdown
from .render import RenderizadorMarkdown
from .theme import cores_interface

EDITAR = 'editar'
PREVIEW = 'preview'
DIVIDIDO = 'dividido'
MODOS = (EDITAR, PREVIEW, DIVIDIDO)
PROXIMO = {EDITAR: PREVIEW, PREVIEW: DIVIDIDO, DIVIDIDO: EDITAR}

DEBOUNCE_MS = 250
DEBOUNCE_TEXTO_GRANDE_MS = 800
LIMITE_TEXTO_GRANDE = 200_000
LARGURA_MINIMA_PAINEL = 120
# A alca do splitter e mais larga que a linha desenhada nela: a linha fina
# marca a divisao, e a margem transparente em volta e a area de arrastar.
LARGURA_ALCA = 9


class PainelNota(QWidget):
    def __init__(self, fonte, tema, fontes, debounce_ms=DEBOUNCE_MS, parent=None):
        super().__init__(parent)
        self.tema = tema
        self._render = RenderizadorMarkdown(tema, fontes)
        self._modo = EDITAR
        self._proporcao = [1, 1]
        self._sujo = False
        self._sincronizando = False
        self._renders = 0  # contador, usado nos testes

        self.editor = EditorMarkdown(fonte, tema)
        self.preview = QTextBrowser()
        self._preparar_preview(fonte)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(LARGURA_ALCA)
        self.splitter.addWidget(self.editor)
        self.splitter.addWidget(self.preview)
        self.editor.setMinimumWidth(LARGURA_MINIMA_PAINEL)
        self.preview.setMinimumWidth(LARGURA_MINIMA_PAINEL)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.splitter)

        # QTimer como membro, nao a estatica QTimer.singleShot: a estatica nao
        # pode ser cancelada nem reiniciada, e enfileiraria uma renderizacao
        # por tecla digitada. E a diferenca entre debounce e desastre.
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(debounce_ms)
        self._timer.timeout.connect(self._renderizar)

        self.editor.textChanged.connect(self._agendar)
        self.editor.verticalScrollBar().valueChanged.connect(self._sincronizar)
        self.splitter.splitterMoved.connect(self._guardar_proporcao)

        self._estilizar_divisao()
        self.definir_modo(EDITAR)

    def _estilizar_divisao(self):
        """Linha vertical de 1px no meio da alca, na cor das barras '='."""
        cor = cores_interface(self.tema)['separador']
        meio_ini = (LARGURA_ALCA // 2) / LARGURA_ALCA
        meio_fim = (LARGURA_ALCA // 2 + 1) / LARGURA_ALCA
        self.splitter.setStyleSheet(
            "QSplitter::handle:horizontal { background: qlineargradient("
            "x1:0, y1:0, x2:1, y2:0, "
            f"stop:0 transparent, stop:{meio_ini:.3f} transparent, "
            f"stop:{meio_ini:.3f} {cor}, stop:{meio_fim:.3f} {cor}, "
            f"stop:{meio_fim:.3f} transparent, stop:1 transparent); }}"
        )

    def _preparar_preview(self, fonte):
        self.preview.setFont(fonte)
        self.preview.document().setDefaultFont(fonte)
        self.preview.document().setDefaultStyleSheet(self._render.folha_de_estilo())
        self.preview.setOpenLinks(False)
        self.preview.setReadOnly(True)
        cores = cores_interface(self.tema)
        self.preview.setStyleSheet(
            f"QTextBrowser {{ background-color: {cores['fundo']};"
            f" color: {cores['texto']}; border: none; }}"
        )

    # --- conteudo ----------------------------------------------------------

    def carregar(self, texto, modo=None):
        """Chamado uma vez, ao abrir a nota."""
        self.editor.definir_texto(texto)
        self._sujo = True
        self.definir_modo(modo or self._modo)

    def texto(self):
        """Conteudo cru do editor. Contrato com EditorScreen.on_save."""
        return self.editor.texto()

    # --- modos -------------------------------------------------------------

    def modo(self):
        return self._modo

    def definir_modo(self, modo):
        if modo not in MODOS:
            return
        if modo == DIVIDIDO and self._modo != DIVIDIDO:
            self._guardar_proporcao()

        self._modo = modo
        mostra_editor = modo in (EDITAR, DIVIDIDO)
        mostra_preview = modo in (PREVIEW, DIVIDIDO)

        self.editor.setVisible(mostra_editor)
        self.preview.setVisible(mostra_preview)

        if modo == DIVIDIDO:
            self.splitter.setSizes(self._proporcao)

        if mostra_preview and self._sujo:
            self._renderizar()

        # Esconder o widget com foco move o foco de forma imprevisivel:
        # definir sempre, explicitamente, depois de mudar a visibilidade.
        if mostra_editor:
            self.editor.setFocus()
        else:
            self.preview.setFocus()

    def ciclar(self):
        self.definir_modo(PROXIMO[self._modo])
        return self._modo

    def _guardar_proporcao(self, *_):
        """sizes() devolve 0 para filho oculto; so guarda quando os dois estao."""
        if self._modo == DIVIDIDO:
            tamanhos = self.splitter.sizes()
            if all(t > 0 for t in tamanhos):
                self._proporcao = tamanhos

    def proporcao(self):
        return list(self._proporcao)

    def definir_proporcao(self, proporcao):
        if proporcao and len(proporcao) == 2 and all(p > 0 for p in proporcao):
            self._proporcao = list(proporcao)

    # --- renderizacao ------------------------------------------------------

    def _agendar(self):
        self._sujo = True
        if self.preview.isVisible():
            texto = self.editor.texto()
            intervalo = (DEBOUNCE_TEXTO_GRANDE_MS if len(texto) > LIMITE_TEXTO_GRANDE
                         else self._timer.interval())
            self._timer.setInterval(intervalo)
            self._timer.start()  # start() num timer ativo reinicia a contagem

    def forcar_render(self):
        self._timer.stop()
        self._renderizar()

    def _renderizar(self):
        barra = self.preview.verticalScrollBar()
        maximo = barra.maximum()
        fracao = (barra.value() / maximo) if maximo else 0.0

        self.preview.setHtml(self._render.html(self.editor.texto()))
        self._renders += 1
        self._sujo = False

        self._restaurar_fracao(fracao)

    def _restaurar_fracao(self, fracao):
        """Sem isto o preview salta para o topo a cada tecla.

        setHtml zera o documento E o maximum() da barra, entao restaurar o
        valor absoluto nao serve - restaura-se a fracao. Aplicado duas vezes
        porque, logo apos o setHtml, o layout pode nao estar calculado e
        maximum() devolve 0.
        """
        def aplicar():
            barra = self.preview.verticalScrollBar()
            barra.setValue(round(fracao * barra.maximum()))
        aplicar()
        QTimer.singleShot(0, aplicar)

    def _sincronizar(self, _valor):
        """Rolagem editor -> preview, proporcional e unidirecional.

        Unidirecional elimina de saida o laco de realimentacao em que cada
        barra empurra a outra, que e o que da a esse recurso fama de bugado.
        """
        if self._sincronizando or self._modo != DIVIDIDO:
            return
        self._sincronizando = True
        try:
            origem = self.editor.verticalScrollBar()
            destino = self.preview.verticalScrollBar()
            fracao = origem.value() / origem.maximum() if origem.maximum() else 0.0
            destino.setValue(round(fracao * destino.maximum()))
        finally:
            self._sincronizando = False

    def recarregar_cores(self, tema, fontes):
        self.tema = tema
        self._render = RenderizadorMarkdown(tema, fontes)
        self.editor.recarregar_cores(tema)
        self._preparar_preview(self.editor.font())
        self._estilizar_divisao()
        if self.preview.isVisible():
            self.forcar_render()
