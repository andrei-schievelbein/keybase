"""App: pilha de telas, bindings e ciclo de vida.

O despachante inteiro cabe em tres linhas porque cada tela sabe tratar o
proprio input:

    def submit(self):
        comando = self.view.ler_entrada()
        self.view.limpar_entrada()
        self.atual.handle_input(comando)

A pilha guarda TELAS, nao nos: uma pilha de nos nao expressaria "prompt sobre
browser sobre browser", e voltar precisa restaurar o browser anterior com o
filtro que ele tinha, que vive na instancia da tela.
"""

from .. import storage
from ..model import ID_RAIZ
from ..tree import construir_indice


class App:
    def __init__(self, root, view, doc, caminho_dados, config):
        self.root = root
        self.view = view
        self.doc = doc
        self.caminho_dados = caminho_dados
        self.config = config
        self.stack = []
        self._flash = None
        self._flash_erro = False
        self.indice = construir_indice(doc.raiz)

    # --- arvore ------------------------------------------------------------

    @property
    def raiz(self):
        return self.doc.raiz

    def reindexar(self):
        self.indice = construir_indice(self.doc.raiz)

    def no(self, node_id):
        """Nó pelo id, ou None se foi removido por baixo da tela."""
        entrada = self.indice.get(node_id)
        return entrada[0] if entrada else None

    def pai_de(self, node_id):
        entrada = self.indice.get(node_id)
        return entrada[1] if entrada else None

    def caminho_de(self, node_id):
        from ..tree import caminho
        no = self.no(node_id)
        return caminho(self.indice, no) if no else []

    def persistir(self):
        """Grava a arvore. Reporta falha na tela, nunca explode em silencio."""
        self.reindexar()
        try:
            storage.salvar(self.doc, self.caminho_dados)
        except storage.StorageError as e:
            self.flash(f"Não foi possível salvar: {e}", erro=True)
            self.doc.marcar_sujo()
            return False
        return True

    def snapshot(self):
        """Forca backup antes de uma operacao destrutiva."""
        try:
            storage.snapshot(self.doc, self.caminho_dados)
        except OSError:
            pass

    # --- pilha -------------------------------------------------------------

    @property
    def atual(self):
        return self.stack[-1] if self.stack else None

    def push(self, tela):
        self.stack.append(tela)
        self.rerender()

    def pop(self, n=1):
        for _ in range(n):
            if len(self.stack) > 1:
                self.stack.pop()
        self.rerender()

    def replace(self, tela):
        if self.stack:
            self.stack.pop()
        self.stack.append(tela)
        self.rerender()

    def reset(self, telas):
        self.stack = list(telas)
        self.rerender()

    def go_root(self):
        from .screens.browser import BrowserScreen
        self.reset([BrowserScreen(self, ID_RAIZ)])

    # --- render ------------------------------------------------------------

    def flash(self, mensagem, erro=False):
        """Mensagem one-shot, consumida no proximo render.

        Tem lugar fixo no layout - na versao anterior o status era injetado em
        "1.0" no meio do conteudo ja renderizado. Truncada porque pode conter o
        nome de um item, que o usuario controla e pode ser bem longo.
        """
        from .layout import truncar
        self._flash = truncar(mensagem, self.view.colunas() - 4)
        self._flash_erro = erro

    def consumir_flash(self):
        msg, erro = self._flash, self._flash_erro
        self._flash = None
        self._flash_erro = False
        return msg, erro

    def rerender(self):
        """Descarta telas cujo no sumiu, recarrega e repinta a do topo."""
        while self.stack:
            tela = self.stack[-1]
            tela.on_enter()
            if getattr(tela, 'descartada', False) and len(self.stack) > 1:
                self.stack.pop()
                continue
            break

        if not self.stack:
            self.go_root()
            return

        tela = self.stack[-1]
        if tela.usa_editor():
            self.view.dica(tela.help_text())
            tela.render()
        else:
            self.view.modo_leitura()
            self.view.limpar()
            tela.render()
            self.view.ao_topo()
            self.view.dica(tela.help_text())

    # --- eventos -----------------------------------------------------------

    def submit(self, event=None):
        comando = self.view.ler_entrada()
        self.view.limpar_entrada()
        if self.atual:
            self.atual.handle_input(comando)
        return "break"

    def save(self, event=None):
        """Ctrl+S vai direto ao metodo da tela ativa.

        Substitui o hack de injetar a sentinela 'CTRL_S' no campo de entrada,
        que truncava qualquer nota terminada nessa palavra.
        """
        if self.atual:
            self.atual.on_save()
        return "break"

    def cancel(self, event=None):
        if self.atual:
            self.atual.on_cancel()
        return "break"

    def sair(self):
        from ..config import salvar_config
        storage.salvar_se_sujo(self.doc, self.caminho_dados)
        salvar_config(self.root, self.config)
        self.root.destroy()

    def ao_fechar(self):
        self.sair()
