"""EditorScreen: edicao do Markdown cru, com os modos editar/preview/dividido.

Ctrl+S salva e Esc cancela, chamando diretamente os metodos desta tela. Nao ha
sentinela nenhuma: a versao antiga injetava a string 'CTRL_S' no campo de
entrada e depois tentava remove-la do texto, o que truncava qualquer nota
terminada nessa palavra. `on_save` le `view.texto_editor()`, que e
toPlainText() puro.

Esta e a UNICA tela que implementa `on_modo`/`on_ciclar_modo` - por isso os
atalhos Ctrl+1/2/3 e Ctrl+E sao inertes em qualquer outro lugar do app.
"""

from ... import tree
from ...model import File
from .. import atalhos
from ..layout import montar_breadcrumb
from ..painel_nota import DIVIDIDO, EDITAR, MODOS, PREVIEW
from .base import Screen
from .prompt import ConfirmScreen

ROTULO = {EDITAR: 'editar', PREVIEW: 'preview', DIVIDIDO: 'dividido'}


class EditorScreen(Screen):
    # A area de leitura da lugar ao painel de edicao: nao ha menu aqui, e o
    # Ctrl+0 fica inerte - um rerender nao pode passar perto do texto nao salvo.
    MOSTRA_MENU = False

    def __init__(self, app, file_id):
        super().__init__(app)
        self.file_id = file_id
        self.file = None
        self.texto_original = ""
        self.descartada = False
        self._carregado = False

    def on_enter(self):
        no = self.app.no(self.file_id)
        if no is None or not isinstance(no, File):
            self.descartada = True
            self.file = None
            return
        self.file = no
        self.descartada = False
        if not self._carregado:
            self.texto_original = no.conteudo

    def usa_editor(self):
        return True

    def render(self):
        if self.file is None:
            return
        # A guarda impede que um rerender (disparado por um flash, por exemplo)
        # recarregue texto_original por cima do que esta sendo digitado.
        if not self._carregado:
            self.app.view.modo_edicao(self.texto_original, modo=self._modo_inicial())
            self._carregado = True

    def _modo_inicial(self):
        return self.app.config.get('editor', {}).get('modo', EDITAR)

    def help_text(self):
        cadeia = self.app.caminho_de(self.file_id)
        atual = self.app.view.modo_edicao_atual()
        trilha = "  ".join(f"[{ROTULO[m]}]" if m == atual else f" {ROTULO[m]} "
                           for m in MODOS)
        r = atalhos.rotulo
        return (f"Editando: {montar_breadcrumb(cadeia)}   ·   {trilha}\n"
                f"{r(atalhos.SALVAR)} salva · {r(atalhos.CANCELAR)} cancela · "
                f"{r(atalhos.MODO_EDITAR)} editar · {r(atalhos.MODO_PREVIEW)} preview · "
                f"{r(atalhos.MODO_DIVIDIDO)} dividido · {r(atalhos.MODO_CICLAR)} alterna")

    def handle_input(self, texto):
        """O Enter do campo de entrada nao age durante a edicao."""
        self.app.flash(f"Use {atalhos.rotulo(atalhos.SALVAR)} para salvar "
                       f"ou {atalhos.rotulo(atalhos.CANCELAR)} para cancelar.")
        self.app.view.focar_editor()

    # --- modos -------------------------------------------------------------

    def on_modo(self, modo):
        if self.file is None or modo not in MODOS:
            return
        self.app.view.definir_modo_edicao(modo)
        self.app.config.setdefault('editor', {})['modo'] = modo
        # Sem rerender: ele chamaria render(), e o texto nao salvo e sagrado.
        # So a barra de dica precisa refletir o modo novo.
        self.app.view.dica(self.help_text())

    def on_ciclar_modo(self):
        if self.file is None:
            return
        modo = self.app.view.ciclar_modo_edicao()
        self.app.config.setdefault('editor', {})['modo'] = modo
        self.app.view.dica(self.help_text())

    # --- salvar e cancelar -------------------------------------------------

    def _alterado(self):
        return self.app.view.texto_editor() != self.texto_original

    def on_save(self):
        if self.file is None:
            return
        texto = self.app.view.texto_editor()  # cru, sem tratar sentinela nenhuma
        tree.definir_conteudo(self.file, texto)
        self.texto_original = texto
        if self.app.persistir():
            self.app.flash("Salvo.")
        self.app.pop()  # volta ao viewer, que rele do modelo e re-renderiza

    def on_cancel(self):
        if self.file is not None and self._alterado():
            # A ConfirmScreen ja se desempilha antes de chamar o callback, entao
            # aqui basta remover o proprio editor - um pop(2) levaria o viewer junto.
            self.app.push(ConfirmScreen(
                self.app,
                "Descartar as alterações não salvas?",
                self.app.pop,
                detalhe=f"Nota: {self.file.nome}",
            ))
            return
        self.app.pop()

    def on_back(self):
        self.on_cancel()
