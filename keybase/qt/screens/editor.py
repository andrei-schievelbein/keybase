"""EditorScreen: edicao do Markdown cru, com os modos editar/preview/dividido.

Ctrl+S salva e Esc cancela, chamando diretamente os metodos desta tela. Nao ha
sentinela nenhuma: a versao antiga injetava a string 'CTRL_S' no campo de
entrada e depois tentava remove-la do texto, o que truncava qualquer nota
terminada nessa palavra. `on_save` le `view.texto_editor()`, que e
toPlainText() puro.

Esta e a UNICA tela que implementa `on_modo`/`on_ciclar_modo` - por isso os
atalhos Ctrl+1/2/3 e Ctrl+E sao inertes em qualquer outro lugar do app.
"""

from ... import cripto, tree
from ...model import File
from .. import atalhos
from ..layout import montar_breadcrumb
from ..painel_nota import DIVIDIDO, EDITAR, MODOS, PREVIEW
from .base import Screen
from .prompt import ConfirmScreen

ROTULO = {EDITAR: 'EDITAR', PREVIEW: 'PREVIEW', DIVIDIDO: 'DIVIDIDO'}


class EditorScreen(Screen):
    # O menu daqui nao vai na area de leitura (escondida pelo painel), e sim na
    # barra de dica: a lista de atalhos de edicao. '?' na barra, Ctrl+0 e o
    # botao alternam o mesmo app.menu_visivel das outras telas - sem rerender,
    # que nao pode passar perto do texto nao salvo.
    MOSTRA_MENU = True
    #: sem realce de Markdown (a tela de configuracao edita TOML)
    TEXTO_PURO = False

    def __init__(self, app, file_id):
        super().__init__(app)
        self.file_id = file_id
        self.file = None
        self.texto_original = ""
        self.descartada = False
        self._carregado = False

    def on_enter(self):
        no = self.app.no(self.file_id)
        # conteudo None = cifrada e trancada: nao ha texto para editar
        if no is None or not isinstance(no, File) or (
                no.conteudo is None and not self._carregado):
            self.descartada = True
            self.file = None
            return
        self.file = no
        self.descartada = False
        if not self._carregado:
            self.texto_original = no.conteudo

    def usa_editor(self):
        return True

    # --- ganchos para quem edita outra coisa que nao uma nota ---------------

    def _ativo(self):
        """Ha o que editar. Uma nota: ela existe e nao esta trancada."""
        return self.file is not None

    def _rotulo_descarte(self):
        return f"Nota: {self.file.nome}"

    def render(self):
        if not self._ativo():
            return
        # A guarda impede que um rerender (disparado por um flash, por exemplo)
        # recarregue texto_original por cima do que esta sendo digitado.
        if not self._carregado:
            self.app.view.modo_edicao(self.texto_original, modo=self._modo_inicial(),
                                      texto_puro=self.TEXTO_PURO)
            self._carregado = True
        else:
            # voltando da ajuda completa: o texto continua no painel
            self.app.view.retomar_edicao()
        self._atualizar_barra()

    def _modo_inicial(self):
        return self.app.config.get('editor', {}).get('modo', EDITAR)

    def help_text(self):
        """O menu de atalhos, abaixo do cabecalho; None o esconde."""
        if not self.app.menu_visivel:
            return None
        return "\n".join(self._menu_atalhos())

    def _atualizar_barra(self):
        """Cabecalho (modos, caminho, divisoria) e menu. Sem rerender."""
        if self.file is None:
            return
        view = self.app.view
        marca = "[cifrada] " if self.file.cifrado else ""
        caminho = montar_breadcrumb(self.app.caminho_de(self.file_id))
        view.cabecalho_edicao([ROTULO[m] for m in MODOS],
                              ROTULO[view.modo_edicao_atual()],
                              f"Editando: {marca}{caminho}")
        view.dica(self.help_text())

    def _menu_atalhos(self):
        """Atalhos de edicao em duas colunas: Ctrl+0..3 a esquerda, o resto a direita."""
        r = atalhos.rotulo
        esquerda = [
            (r(atalhos.AJUDA_DINAMICA), "Esconder atalhos (ou ?)"),
            (r(atalhos.MODO_EDITAR), "Só o editor"),
            (r(atalhos.MODO_PREVIEW), "Só o preview"),
            (r(atalhos.MODO_DIVIDIDO), "Dividido"),
        ]
        direita = [
            (r(atalhos.SALVAR), "Salvar e voltar"),
            (r(atalhos.CANCELAR), "Ir para a barra"),
            (r(atalhos.MODO_CICLAR), "Alternar modo"),
            ("??", "Ajuda completa"),
        ]
        largura_tecla = max(len(tecla) for tecla, _ in esquerda + direita)

        def celula(par):
            return f"{par[0]:>{largura_tecla}} - {par[1]}"

        coluna = max(len(celula(p)) for p in esquerda) + 4
        return [(celula(e).ljust(coluna) + celula(d)).rstrip()
                for e, d in zip(esquerda, direita)]

    def handle_input(self, texto):
        """Na barra, so '?' (menu) e '??' (ajuda) agem durante a edicao.

        '?' digitado no EDITOR e texto da nota: e outro widget, nem passa aqui.
        """
        texto = (texto or "").strip()
        if texto == '?':
            return self.on_ajuda()
        if texto == '??':
            return self.cmd_ajuda_completa()
        if not texto:
            # Enter vazio na barra: volta para o texto (o caminho inverso do Esc)
            self.app.view.focar_editor()
            return
        self.app.flash(f"Use {atalhos.rotulo(atalhos.SALVAR)} para salvar "
                       f"ou {atalhos.rotulo(atalhos.CANCELAR)} para cancelar.")
        self.app.view.focar_editor()

    def on_ajuda(self):
        """Alterna o menu de atalhos na barra de dica, sem tocar no texto."""
        if not self._ativo():
            return
        self.app.menu_visivel = not self.app.menu_visivel
        self._atualizar_barra()
        self.app.view.focar_editor()

    # --- modos -------------------------------------------------------------

    def on_modo(self, modo):
        if self.file is None or modo not in MODOS:
            return
        self.app.view.definir_modo_edicao(modo)
        self.app.config.setdefault('editor', {})['modo'] = modo
        # Sem rerender: ele chamaria render(), e o texto nao salvo e sagrado.
        # So o cabecalho precisa refletir o modo novo.
        self._atualizar_barra()

    def on_ciclar_modo(self):
        if self.file is None:
            return
        modo = self.app.view.ciclar_modo_edicao()
        self.app.config.setdefault('editor', {})['modo'] = modo
        self._atualizar_barra()

    # --- salvar e cancelar -------------------------------------------------

    def _alterado(self):
        return self.app.view.texto_editor() != self.texto_original

    def on_save(self):
        if self.file is None:
            return
        texto = self.app.view.texto_editor()  # cru, sem tratar sentinela nenhuma
        if self.file.cifrado:
            try:
                cripto.selar(self.app.cofre, self.file, texto)
            except cripto.CofreTrancadoError:
                # nao deveria acontecer (o auto-trancar espera o editor), mas se
                # acontecer o texto fica na tela em vez de sumir
                self.app.flash("As notas cifradas foram trancadas; nada foi salvo.",
                               erro=True)
                self._atualizar_barra()
                return
        else:
            tree.definir_conteudo(self.file, texto)
        self.texto_original = texto
        if self.app.persistir():
            self.app.flash("Salvo.")
        self.app.pop()  # volta ao viewer, que rele do modelo e re-renderiza

    def on_cancel(self):
        """Esc no texto leva o cursor para a barra; Esc na barra cancela."""
        if self.app.view.foco_na_edicao():
            self.app.view.focar_entrada()
            return
        if self._ativo() and self._alterado():
            # A ConfirmScreen ja se desempilha antes de chamar o callback, entao
            # aqui basta remover o proprio editor - um pop(2) levaria o viewer junto.
            self.app.push(ConfirmScreen(
                self.app,
                "Descartar as alterações não salvas?",
                self.app.pop,
                detalhe=self._rotulo_descarte(),
            ))
            return
        self.app.pop()

    def on_back(self):
        self.on_cancel()
