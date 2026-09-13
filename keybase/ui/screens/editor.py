"""EditorScreen: edicao do Markdown cru, num widget proprio.

Todo conteudo multilinha passa por aqui. Ctrl+S salva, Esc cancela - e os dois
chamam diretamente os metodos desta tela, sem o hack de sentinelas da versao
anterior, que injetava a string 'CTRL_S' no campo de entrada e depois tentava
remove-la do texto, truncando qualquer nota terminada nessa palavra.
"""

from ... import tree
from ...model import File
from ..layout import montar_breadcrumb
from .base import Screen
from .prompt import ConfirmScreen


class EditorScreen(Screen):
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
        if not self._carregado:
            self.app.view.modo_edicao(self.texto_original)
            self._carregado = True

    def help_text(self):
        cadeia = self.app.caminho_de(self.file_id)
        return (f"Editando: {montar_breadcrumb(cadeia)}\n"
                f"Ctrl+S salva  ·  Esc cancela  ·  Markdown com ```linguagem "
                f"para blocos de código")

    def handle_input(self, texto):
        """O Enter do campo de entrada nao age durante a edicao."""
        self.app.flash("Use Ctrl+S para salvar ou Esc para cancelar.")
        self.app.view.edit.focus_set()

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
