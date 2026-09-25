"""FavoritosScreen: favoritos (F) e notas abertas recentemente, abertas com L.

Uma numeracao so para as duas listas: favoritos primeiro, depois recentes.
self.itens e exatamente o que foi impresso - a mesma invariante do browser.

So entra o que esta visivel na arvore: um item dentro de uma pasta cifrada
trancada nao aparece ate a pasta ser destrancada (os recentes guardam so ids).
"""

from ... import tree
from ...model import Folder
from ..layout import LARGURA_NUMERO, truncar
from .base import Screen


def _linhas(numero, no, caminho, largura):
    prefixo = f"{numero:>{LARGURA_NUMERO}} - "
    recuo = " " * len(prefixo)
    nome = no.nome + ("/" if isinstance(no, Folder) else "")
    return [
        [(prefixo, 'numero'), (truncar(nome, largura - len(prefixo)),
                               'pasta' if isinstance(no, Folder) else 'nota')],
        [(recuo, None), (truncar(caminho, largura - len(recuo)), 'contador')],
    ]


class FavoritosScreen(Screen):
    COMANDOS = {'V': 'cmd_voltar', 'M': 'cmd_raiz', 'C': 'cmd_config'}
    ROTULOS = {'V': 'Voltar', 'M': 'Ir para a raiz', 'C': 'Configuração'}

    def __init__(self, app):
        super().__init__(app)
        self.favoritos = []
        self.recentes = []

    @property
    def itens(self):
        return self.favoritos + self.recentes

    def on_enter(self):
        self.favoritos = [no for no, _ in tree.percorrer(self.app.raiz) if no.favorito]
        self.recentes = [no for no in (self.app.no(i) for i in self.app.recentes())
                         if no is not None]

    def _caminho(self, no):
        cadeia = self.app.caminho_de(no.id)[:-1]
        return tree.breadcrumb(cadeia) or "(raiz)"

    def render(self):
        view = self.app.view
        largura = view.colunas()
        msg, erro = self.app.consumir_flash()
        view.cabecalho(msg if msg else "FAVORITOS E RECENTES",
                       ('erro' if erro else 'flash') if msg else 'breadcrumb')

        numero = 1
        view.linha(" Favoritos", 'pasta')
        if not self.favoritos:
            view.linha(" Nenhum favorito. Use F3 na lista para marcar o item 3.", 'vazio')
        for no in self.favoritos:
            for partes in _linhas(numero, no, self._caminho(no), largura):
                view.trechos(partes)
            numero += 1
        view.linha()
        view.linha(" Abertas recentemente", 'pasta')
        if not self.recentes:
            view.linha(" Nenhuma nota aberta ainda.", 'vazio')
        for no in self.recentes:
            for partes in _linhas(numero, no, self._caminho(no), largura):
                view.trechos(partes)
            numero += 1
        view.barra()

    def selecionar(self, indice):
        if not (0 <= indice < len(self.itens)):
            self.app.flash("Número fora da lista.", erro=True)
            self.app.rerender()
            return
        self.app.abrir_no(self.itens[indice])

    def cmd_voltar(self, alvo=None):
        self.app.pop()

    def cmd_raiz(self, alvo=None):
        self.app.go_root()
