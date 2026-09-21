"""ViewerScreen: exibe uma nota com o Markdown renderizado."""

from ... import tree
from ...model import File
from ..layout import montar_breadcrumb
from .base import Screen
from .prompt import ConfirmScreen, PromptScreen


class ViewerScreen(Screen):
    COMANDOS = {
        'E': 'cmd_editar',
        'R': 'cmd_renomear',
        'D': 'cmd_deletar',
        'V': 'cmd_voltar',
        'M': 'cmd_raiz',
    }
    ROTULOS = {
        'E': 'Editar nota', 'R': 'Renomear', 'D': 'Deletar',
        'V': 'Voltar', 'M': 'Ir para a raiz',
    }

    def __init__(self, app, file_id):
        super().__init__(app)
        self.file_id = file_id
        self.file = None
        self.descartada = False

    def on_enter(self):
        no = self.app.no(self.file_id)
        if no is None or not isinstance(no, File):
            self.descartada = True
            self.file = None
            return
        self.file = no
        self.descartada = False

    def render(self):
        view = self.app.view
        cadeia = self.app.caminho_de(self.file_id)

        view.cabecalho(montar_breadcrumb(cadeia, view.colunas() - 2))

        msg, erro = self.app.consumir_flash()
        if msg:
            view.linha(" " + msg, 'erro' if erro else 'flash')
            view.barra()

        # O cabecalho vai ANTES do markdown. Na versao anterior ele era inserido
        # em "1.0" depois da renderizacao, deslocando as tags ja posicionadas.
        if self.file is not None:
            if self.file.conteudo.strip():
                view.markdown(self.file.conteudo)
            else:
                view.linha(" Nota vazia. Use E para escrever o conteúdo.", 'vazio')

        view.barra()

    def help_text(self):
        return None

    def selecionar(self, indice):
        self.app.flash("Esta tela não tem lista. Use E para editar.", erro=True)
        self.app.rerender()

    # --- comandos ----------------------------------------------------------

    def cmd_editar(self, alvo=None):
        from .editor import EditorScreen
        self.app.push(EditorScreen(self.app, self.file_id))

    def cmd_voltar(self, alvo=None):
        self.app.pop()

    def cmd_raiz(self, alvo=None):
        self.app.go_root()

    def cmd_renomear(self, alvo=None):
        pai = self.app.pai_de(self.file_id)
        if pai is None:
            return

        def validar(nome):
            if not nome:
                return "O nome não pode ficar vazio."
            if not tree.nome_disponivel(pai, nome, ignorar=self.file):
                return f"Já existe um item chamado {nome!r} nesta pasta."
            return None

        def aplicar(nome):
            tree.renomear(self.file, nome)
            self.app.persistir()
            self.app.flash(f"Renomeado para {nome!r}.")
            self.app.rerender()

        self.app.push(PromptScreen(
            self.app, f"Novo nome para {self.file.nome!r}:", aplicar,
            valor_inicial=self.file.nome, validar=validar,
            contexto=montar_breadcrumb(self.app.caminho_de(self.file_id)),
        ))

    def cmd_deletar(self, alvo=None):
        pai = self.app.pai_de(self.file_id)
        if pai is None:
            return
        nome = self.file.nome

        def aplicar():
            self.app.snapshot()
            tree.remover(pai, self.file)
            self.app.persistir()
            self.app.pop()  # sai do viewer: o no nao existe mais
            self.app.flash(f"{nome!r} foi removido.")
            self.app.rerender()

        self.app.push(ConfirmScreen(
            self.app, f"Apagar {tree.resumo_delecao(self.file)}?", aplicar,
        ))
