"""Janela principal: layout, atalhos e ciclo de vida.

A janela nao sabe qual tela esta ativa - ela so traduz tecla em verbo e
entrega ao App, que despacha para a tela do topo da pilha. Como os metodos
correspondentes sao no-op na classe Screen, um atalho de modo apertado fora do
editor simplesmente nao faz nada, sem nenhum `if` aqui.
"""

import re

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import QVBoxLayout, QWidget

from . import atalhos
from .painel_nota import DIVIDIDO, EDITAR, PREVIEW
from .theme import cores_interface
from .view import TerminalView

ATRASO_RESIZE_MS = 120
INTERVALO_COFRE_MS = 30_000
TAMANHO_MINIMO = (400, 300)

PADRAO_GEOMETRIA = re.compile(
    r'^\s*(\d+)\s*x\s*(\d+)(?:([+-])(-?\d+)([+-])(-?\d+))?\s*$'
)


def parse_geometria(texto):
    """'800x600+100+50' -> (800, 600, 100, 50). None se nao casar.

    Aceita a forma que o Tk gravava para coordenada negativa ('+-1566'), que e
    o que ha nos arquivos de configuracao existentes.
    """
    casamento = PADRAO_GEOMETRIA.match(texto or '')
    if not casamento:
        return None
    largura, altura = int(casamento.group(1)), int(casamento.group(2))
    if casamento.group(3) is None:
        return largura, altura, None, None
    x = int(casamento.group(4)) * (-1 if casamento.group(3) == '-' else 1)
    y = int(casamento.group(6)) * (-1 if casamento.group(5) == '-' else 1)
    return largura, altura, x, y


def formatar_geometria(largura, altura, x, y):
    return f"{largura}x{altura}+{x}+{y}"


def ajustar_a_area(largura, altura, x, y, areas):
    """Encaixa a janela numa das areas disponiveis.

    Funcao pura (recebe retangulos, nao consulta o sistema) para poder ser
    testada sem display. Resolve o caso real de uma geometria salva num monitor
    secundario que nao existe mais - hoje a janela abriria fora da tela.
    """
    if not areas:
        return largura, altura, x or 0, y or 0

    largura = max(TAMANHO_MINIMO[0], largura)
    altura = max(TAMANHO_MINIMO[1], altura)

    if x is None or y is None:
        ax, ay, aw, ah = areas[0]
        largura, altura = min(largura, aw), min(altura, ah)
        return largura, altura, ax + (aw - largura) // 2, ay + (ah - altura) // 2

    def intersecao(area):
        ax, ay, aw, ah = area
        dx = max(0, min(x + largura, ax + aw) - max(x, ax))
        dy = max(0, min(y + altura, ay + ah) - max(y, ay))
        return dx * dy

    melhor = max(areas, key=intersecao)
    if intersecao(melhor) == 0:
        # a geometria salva nao alcanca tela nenhuma: centraliza na primaria
        ax, ay, aw, ah = areas[0]
        largura, altura = min(largura, aw), min(altura, ah)
        return largura, altura, ax + (aw - largura) // 2, ay + (ah - altura) // 2

    ax, ay, aw, ah = melhor
    largura, altura = min(largura, aw), min(altura, ah)
    x = min(max(x, ax), ax + aw - largura)
    y = min(max(y, ay), ay + ah - altura)
    return largura, altura, x, y


class JanelaPrincipal(QWidget):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.app = None
        self._encerrando = False
        self._colunas_pintadas = None

        self.setWindowTitle("KeyBase")
        self.view = TerminalView(config, self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)

        # limpeza da area de transferencia depois de copiar algo cifrado
        self._timer_copia = QTimer(self)
        self._timer_copia.setSingleShot(True)
        self._limpar_copia = None
        self._timer_copia.timeout.connect(lambda: self._limpar_copia and self._limpar_copia())

        # um timer so, reiniciado a cada aviso: o mais novo manda
        self._timer_flash = QTimer(self)
        self._timer_flash.setSingleShot(True)
        self._fim_do_flash = None
        self._timer_flash.timeout.connect(self._ao_fim_do_flash)

        self._timer_resize = QTimer(self)
        self._timer_resize.setSingleShot(True)
        self._timer_resize.timeout.connect(self._ao_reajustar)

        self.setStyleSheet(self._folha())

    def _folha(self):
        c = cores_interface(self.config['theme'])
        return f"""
        QWidget {{ background-color: {c['fundo']}; color: {c['texto']}; }}
        QLineEdit#entrada {{
            background-color: {c['entrada_bg']};
            border: 1px solid {c['entrada_borda']};
            border-radius: 4px;
            padding: 6px;
            selection-background-color: {c['selecao']};
            selection-color: {c['selecao_texto']};
        }}
        QToolButton#botao_ajuda {{
            background-color: {c['entrada_bg']};
            color: {c['texto']};
            border: 1px solid {c['entrada_borda']};
            border-radius: 4px;
        }}
        QToolButton#botao_ajuda:hover {{
            background-color: {c['selecao']};
            color: {c['selecao_texto']};
        }}
        /* Apagado nas telas sem menu (prompt, editor, ajuda): o clique ali seria
           inerte, e um botao vivo que nao faz nada parece defeito. */
        QToolButton#botao_ajuda:disabled {{
            background-color: {c['fundo']};
            color: {c['entrada_borda']};
        }}
        QLabel#ajuda {{
            background-color: {c['help_bg']};
            color: {c['help_fg']};
            padding: 6px;
        }}
        QWidget#cabecalho_edicao, QWidget#cabecalho_edicao QLabel {{
            background-color: {c['help_bg']};
            color: {c['help_fg']};
        }}
        QWidget#cabecalho_edicao QLabel#edicao_divisoria {{
            color: {c['separador']};
        }}
        QWidget#cabecalho_edicao QLabel#edicao_aviso {{
            color: {c['flash']};
        }}
        QWidget#cabecalho_edicao QLabel#edicao_erro {{
            color: {c['erro']};
        }}
        /* Sem o fundo do menu: e so a linha entre o menu e o texto. */
        QLabel#ajuda_divisoria {{
            color: {c['separador']};
        }}
        QTextBrowser, QPlainTextEdit {{
            background-color: {c['fundo']};
            color: {c['texto']};
            border: none;
            selection-background-color: {c['selecao']};
            selection-color: {c['selecao_texto']};
        }}
        /* A barra da area de leitura fica sempre visivel (para a largura do
           viewport nao depender do conteudo e nao gerar laco de repintura),
           entao precisa ser discreta. */
        QScrollBar:vertical {{
            background: transparent; width: 10px; margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {c['entrada_borda']};
            border-radius: 5px; min-height: 24px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0; border: none; background: none;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
        }}
        """

    # --- ligacao com o App -------------------------------------------------

    def agendar_limpeza_copia(self, ms, callback):
        self._limpar_copia = callback
        self._timer_copia.start(ms)

    def agendar_fim_do_flash(self, ms, callback):
        self._fim_do_flash = callback
        self._timer_flash.start(ms)

    def _ao_fim_do_flash(self):
        if self._fim_do_flash is not None and not self._encerrando:
            self._fim_do_flash()

    def aplicar_tema(self, tema):
        """Troca o tema com o app aberto: paleta, folha da janela e a view."""
        from PySide6.QtWidgets import QApplication

        from .estilo import aplicar_tema
        qapp = QApplication.instance()
        if qapp is not None:
            aplicar_tema(qapp, tema)
        self.setStyleSheet(self._folha())  # _folha le self.config['theme']
        self.view.aplicar_tema(tema)

    def ligar(self, app):
        self.app = app
        self.view.entrada.returnPressed.connect(app.submit)
        # o botao e so um terceiro caminho para o mesmo verbo: '?' na barra,
        # Ctrl+0 e o clique alternam exatamente a mesma coisa
        self.view.botao_ajuda.clicked.connect(app.alternar_menu)
        # so a area de leitura: um clique no preview do editor levaria embora
        # da nota com texto nao salvo
        self.view.out.anchorClicked.connect(lambda url: app.abrir_link(url.toString()))
        self._atalhos(app)
        # auto-trancar do cofre: o App decide, o timer so pergunta de tempos em tempos
        self._timer_cofre = QTimer(self)
        self._timer_cofre.setInterval(INTERVALO_COFRE_MS)
        self._timer_cofre.timeout.connect(app.verificar_auto_trancar)
        self._timer_cofre.start()

    def _atalhos(self, app):
        self._registrados = []

        def liga(sequencia, acao):
            # atalhos.variantes registra tambem o Ctrl fisico no macOS, onde o
            # Qt mapeia "Ctrl+X" para Cmd+X
            for combinacao in atalhos.variantes(sequencia):
                atalho = QShortcut(combinacao, self)
                # WindowShortcut: dispara com o foco em QUALQUER widget da
                # janela. E o que faz Ctrl+S e Esc valerem tanto no campo
                # quanto no editor, sem registrar em cada widget.
                atalho.setContext(Qt.ShortcutContext.WindowShortcut)
                atalho.activated.connect(acao)
                self._registrados.append(atalho)

        liga(atalhos.SALVAR, app.save)
        liga(atalhos.CANCELAR, app.cancel)
        liga(atalhos.MODO_EDITAR, lambda: app.modo(EDITAR))
        liga(atalhos.MODO_PREVIEW, lambda: app.modo(PREVIEW))
        liga(atalhos.MODO_DIVIDIDO, lambda: app.modo(DIVIDIDO))
        liga(atalhos.MODO_CICLAR, app.ciclar_modo)
        liga(atalhos.AJUDA_DINAMICA, app.alternar_menu)

        # setas SO na barra de cima (WidgetShortcut): no editor elas movem o
        # cursor do texto, e uma tela de lista nao pode rouba-las de la
        self._setas = []
        for tecla, delta in ((Qt.Key.Key_Up, -1), (Qt.Key.Key_Down, 1)):
            seta = QShortcut(QKeySequence(tecla), self.view.entrada)
            seta.setContext(Qt.ShortcutContext.WidgetShortcut)
            seta.activated.connect(lambda d=delta: app.seta(d))
            self._setas.append(seta)

    # --- geometria ---------------------------------------------------------

    def geometria_texto(self):
        """width()/height() sao da area cliente e casam com resize();
        x()/y() sao do frame e casam com move(). Misturar com geometry() faz a
        janela subir alguns pixels a cada abertura."""
        return formatar_geometria(self.width(), self.height(), self.x(), self.y())

    def aplicar_geometria(self, texto):
        valores = parse_geometria(texto)
        if not valores:
            self.resize(800, 600)
            return
        largura, altura, x, y = valores
        areas = [(t.availableGeometry().x(), t.availableGeometry().y(),
                  t.availableGeometry().width(), t.availableGeometry().height())
                 for t in QGuiApplication.screens()]
        largura, altura, x, y = ajustar_a_area(largura, altura, x, y, areas)
        self.resize(largura, altura)
        self.move(x, y)

    # --- eventos -----------------------------------------------------------

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        self._timer_resize.start(ATRASO_RESIZE_MS)

    def _ao_reajustar(self):
        """Repinta so quando a largura em caracteres realmente mudou.

        Tres guardas contra laco: a repintura nao altera a largura do viewport
        (a barra de rolagem e sempre visivel), a comparacao transforma resize
        sem mudanca de coluna em no-op, e isto roda de um timer, nunca de
        dentro de um paintEvent.
        """
        if self.app is None or self.view.em_edicao():
            return
        agora = self.view.colunas()
        if agora != self._colunas_pintadas:
            self._colunas_pintadas = agora
            self.app.rerender()

    def closeEvent(self, evento):
        # A flag evita a recursao sair() -> close() -> closeEvent() -> sair()
        if not self._encerrando and self.app is not None:
            self._encerrando = True
            self.app.ao_fechar()
        evento.accept()

    def encerrar(self):
        self._encerrando = True
        self.close()
