"""FavoritosScreen: favoritos (F) e notas abertas recentemente, abertas com L.

Uma numeracao so para as duas listas: favoritos primeiro, depois recentes.
self.itens e exatamente o que foi impresso - a mesma invariante do browser.

So entra o que esta visivel na arvore: um item dentro de uma pasta cifrada
trancada nao aparece ate a pasta ser destrancada (os recentes guardam so ids).

D tira da lista: desfavorita o que esta em Favoritos e esquece o que esta em
Recentes. Aceita D3, D1,2, D1-3 e M na pergunta, como no browser - e por
posicao, porque a mesma nota pode estar nas duas listas. X limpa os recentes.
"""

from ... import tree
from ...model import Folder
from ..layout import LARGURA_NUMERO, truncar
from .base import Screen
from .prompt import ConfirmScreen


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
    COMANDOS = {'D': 'cmd_tirar', 'X': 'cmd_limpar_recentes',
                'V': 'cmd_voltar', '/': 'cmd_raiz', 'O': 'cmd_config'}
    ROTULOS = {'D': 'Tirar da lista', 'X': 'Limpar recentes',
               'V': 'Voltar', '/': 'Ir para a raiz', 'O': 'Opções'}
    ACOES_NO_ITEM = {'D': "Tirar {} da lista"}
    COMANDOS_EM_LOTE = ('D',)

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

    def comandos_disponiveis(self):
        ativos = set(self.COMANDOS)
        if not self.itens:
            ativos.discard('D')
        if not self.app.recentes():
            ativos.discard('X')
        return ativos

    def _e_favorito(self, indice):
        """A posicao cai na parte de cima (Favoritos) da numeracao unica."""
        return indice < len(self.favoritos)

    def acao_no_item(self, letra, indice):
        no = self.itens[indice]
        if self._e_favorito(indice):
            return f"Desfavoritar {no.nome!r}"
        return f"Tirar {no.nome!r} dos recentes"

    def _rotulos(self):
        """Cada linha da pergunta e da selecao diz de qual lista o item e."""
        return ([f"{no.nome}  (favorito)" for no in self.favoritos]
                + [f"{no.nome}  (recente)" for no in self.recentes])

    # --- comandos -----------------------------------------------------------

    def cmd_tirar(self, alvo=None):
        self._com_alvo(alvo, "Tirar qual item da lista? (número)",
                       lambda i: self._tirar([i]), varios=self._tirar,
                       verbo="Tirar", por_indice=True, rotulos=self._rotulos())

    def _tirar(self, indices):
        """Desfavorita os de cima e esquece os de baixo, numa gravacao so."""
        favoritos = [self.itens[i] for i in indices if self._e_favorito(i)]
        recentes = {self.itens[i].id for i in indices if not self._e_favorito(i)}
        for no in favoritos:
            no.favorito = False
        if favoritos:
            self.app.persistir()
        if recentes:
            self.app.config['recentes'] = [i for i in self.app.recentes()
                                           if i not in recentes]

        nomes_recentes = [self.itens[i].nome for i in indices if not self._e_favorito(i)]
        partes = []
        for nomes, lista in (([no.nome for no in favoritos], "dos favoritos"),
                             (nomes_recentes, "dos recentes")):
            if len(nomes) == 1:
                partes.append(f"{nomes[0]!r} saiu {lista}")
            elif nomes:
                partes.append(f"{len(nomes)} saíram {lista}")
        self.app.flash(" e ".join(partes) + ".")
        self.app.rerender()

    def cmd_limpar_recentes(self, alvo=None):
        n = len(self.app.recentes())
        if not n:
            self.app.flash("Não há recentes para limpar.")
            self.app.rerender()
            return

        def limpar():
            self.app.config['recentes'] = []
            self.app.flash("Recentes limpos. Os favoritos ficam.")
            self.app.rerender()

        self.app.push(ConfirmScreen(
            self.app, f"Limpar os {n} recentes?" if n > 1 else "Limpar o recente?",
            limpar, detalhe="Só esquece a lista: nenhuma nota é apagada."))

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
