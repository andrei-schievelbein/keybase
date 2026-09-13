"""SearchResultsScreen: resultados da busca global.

Cada Resultado ja carrega seus ancestrais, coletados durante o DFS. Abrir um
hit e reconstruir a pilha de navegacao a partir deles - sem nenhuma busca
reversa, e sem indexar lista de origem alguma.
"""

from ... import search
from ...model import Folder
from ..layout import linha_resultado
from .base import Screen


class SearchResultsScreen(Screen):
    COMANDOS = {
        'B': 'cmd_nova_busca',
        'V': 'cmd_voltar',
        'M': 'cmd_raiz',
        '?': 'cmd_ajuda',
    }
    ROTULOS = {'B': 'nova busca', 'V': 'voltar', 'M': 'raiz', '?': 'ajuda'}

    def __init__(self, app, termo):
        super().__init__(app)
        self.termo = termo
        self.resultados = []
        self.total = 0
        self.erro = None

    def on_enter(self):
        try:
            self.resultados, self.total = search.buscar(self.app.raiz, self.termo)
            self.erro = None
        except search.TermoCurtoError as e:
            self.resultados, self.total = [], 0
            self.erro = str(e)

    def render(self):
        view = self.app.view

        view.trechos([("Busca: ", 'breadcrumb'), (f'"{self.termo}"', 'flash')])
        view.separador()

        if self.erro:
            view.linha()
            view.linha("  " + self.erro, 'erro')
            self.desenhar_rodape()
            return

        if not self.resultados:
            view.linha()
            view.linha("  (nenhum resultado)", 'vazio')
            self.desenhar_rodape()
            return

        plural = "resultados" if self.total != 1 else "resultado"
        if self.total > len(self.resultados):
            view.linha(f"  mostrando {len(self.resultados)} de {self.total} {plural}",
                       'contador')
        else:
            view.linha(f"  {self.total} {plural}", 'contador')
        view.linha()

        for i, resultado in enumerate(self.resultados, start=1):
            for partes in linha_resultado(i, resultado):
                view.trechos(partes)
            view.linha()

        self.desenhar_rodape()

    def comandos_disponiveis(self):
        return set(self.COMANDOS)

    def selecionar(self, indice):
        if not (0 <= indice < len(self.resultados)):
            self.app.flash("Número fora da lista.", erro=True)
            self.app.rerender()
            return

        resultado = self.resultados[indice]
        from .browser import BrowserScreen
        from .viewer import ViewerScreen

        # reconstroi a pilha ate o pai do hit, para que 'voltar' percorra o
        # caminho real da arvore
        pilha = [BrowserScreen(self.app, no.id) for no in resultado.ancestrais]
        pilha.append(self)  # preserva os resultados logo abaixo do hit

        if isinstance(resultado.no, Folder):
            pilha.append(BrowserScreen(self.app, resultado.no.id))
        else:
            pilha.append(ViewerScreen(self.app, resultado.no.id))

        self.app.reset(pilha)

    def cmd_nova_busca(self, alvo=None, resto=None):
        from .prompt import PromptScreen

        def buscar(termo):
            self.app.replace(SearchResultsScreen(self.app, termo))

        self.app.push(PromptScreen(self.app, "Buscar em toda a base:", buscar))

    def cmd_voltar(self, alvo=None, resto=None):
        self.app.pop()

    def cmd_raiz(self, alvo=None, resto=None):
        self.app.go_root()

    def cmd_ajuda(self, alvo=None, resto=None):
        from .help import HelpScreen
        self.app.push(HelpScreen(self.app))

    def cmd_filtro(self, termo):
        self.app.replace(SearchResultsScreen(self.app, termo))
