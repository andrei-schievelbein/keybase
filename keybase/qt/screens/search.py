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
        'C': 'cmd_config',
        'L': 'cmd_favoritos',
    }
    ROTULOS = {'B': 'Nova busca', 'V': 'Voltar', 'M': 'Ir para a raiz',
               'C': 'Configuração', 'L': 'Favoritos e recentes'}

    def __init__(self, app, termo):
        super().__init__(app)
        self.termo = termo
        self.resultados = []
        self.total = 0
        self.erro = None
        self.destaque = -1   # indice escolhido pelas setas; -1 = nenhum

    def on_enter(self):
        try:
            self.resultados, self.total = search.buscar(self.app.raiz, self.termo)
            self.erro = None
        except search.TermoCurtoError as e:
            self.resultados, self.total = [], 0
            self.erro = str(e)

    def render(self):
        view = self.app.view

        view.barra()
        view.trechos([(" Busca: ", 'breadcrumb'), (f'"{self.termo}"', 'flash')])
        view.barra()

        if self.erro:
            view.linha(" " + self.erro, 'erro')
            view.barra()
            return

        if not self.resultados:
            view.linha(" Nenhum resultado.", 'vazio')
            view.barra()
            return

        plural = "resultados" if self.total != 1 else "resultado"
        if self.total > len(self.resultados):
            view.linha(f" Mostrando {len(self.resultados)} de {self.total} {plural}",
                       'contador')
        else:
            view.linha(f" {self.total} {plural}", 'contador')
        view.linha(" Número abre · setas escolhem e ENTER abre o escolhido", 'dica')
        view.linha()

        for i, resultado in enumerate(self.resultados, start=1):
            for partes in linha_resultado(i, resultado, view.colunas(),
                                          destacado=(i - 1 == self.destaque)):
                view.trechos(partes)
            view.linha()

        view.barra()

    def comandos_disponiveis(self):
        return set(self.COMANDOS)

    def on_seta(self, delta):
        if not self.resultados:
            return
        if self.destaque < 0:
            self.destaque = 0 if delta > 0 else len(self.resultados) - 1
        else:
            self.destaque = max(0, min(len(self.resultados) - 1, self.destaque + delta))
        self.app.rerender()
        # o rerender volta ao topo; o destaque pode estar la embaixo
        self.app.view.rolar_ate_texto(f"{self.destaque + 1:>2} - [")

    def on_back(self):
        """Enter vazio: abre o destacado; sem destaque, volta."""
        if self.destaque >= 0:
            return self.selecionar(self.destaque)
        self.app.pop()

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

        if getattr(resultado.no, 'conteudo', "") is None:
            # nota cifrada e trancada: pede a senha antes de abrir
            self.app.exigir_cofre(lambda: self.app.reset(pilha))
            return
        self.app.reset(pilha)

    def cmd_nova_busca(self, alvo=None):
        from .prompt import PromptScreen

        def buscar(termo):
            self.app.replace(SearchResultsScreen(self.app, termo))

        self.app.push(PromptScreen(self.app, "Buscar em toda a base:", buscar))

    def cmd_voltar(self, alvo=None):
        self.app.pop()

    def cmd_raiz(self, alvo=None):
        self.app.go_root()

    def cmd_filtro(self, termo):
        self.app.replace(SearchResultsScreen(self.app, termo))
