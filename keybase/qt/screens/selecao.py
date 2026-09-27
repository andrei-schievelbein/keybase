"""SelecaoScreen: marcar varios itens com setas e espaco (M na pergunta de C, M, Z e D).

Fica por cima da pergunta "qual item?": ESC volta para ela, com o cursor na
barra; ENTER fecha as duas e entrega os marcados. O foco vai para a area de
leitura, que repassa setas, espaco e ENTER (AreaTerminal.tecla_de_lista) -
na barra, o espaco seria so mais um caractere digitado.

Guarda ids e nao nos: um item que some por baixo (trancado por inatividade,
por exemplo) sai da lista em vez de estourar. A marca e por POSICAO na lista
de baixo, nao por id: nos favoritos o mesmo no aparece duas vezes (favorito e
recente), e cada linha e uma escolha diferente.
"""

from ..layout import linha_item, montar_menu_fixo, truncar
from .base import Screen

MARCA = "[X]"
VAZIO = "[ ]"
CURSOR = ">"  # da propria fonte mono: um glifo de fallback engordaria a linha


class SelecaoScreen(Screen):
    MOSTRA_MENU = False  # menu fixo (desenhar_menu): '?' e o botao nao o escondem

    def __init__(self, app, itens, verbo, ao_confirmar, contexto="", rotulos=None):
        super().__init__(app)
        #: ids na ordem exibida pela tela de baixo
        self.ids = [no.id for no in itens]
        #: texto de cada linha no lugar do nome do item (None = o nome)
        self.rotulos = list(rotulos) if rotulos is not None else None
        #: 'Copiar', 'Mover', 'Duplicar', 'Deletar'
        self.verbo = verbo
        #: recebe as posicoes marcadas, na ordem da lista
        self.ao_confirmar = ao_confirmar
        self.contexto = contexto
        self.cursor = 0          # indice em self.visiveis
        self.marcados = set()    # posicoes na lista de baixo
        self.visiveis = []       # [(posicao, no)] dos que ainda existem
        self._erro = None

    def on_enter(self):
        self.visiveis = [(pos, no) for pos, no in
                         ((pos, self.app.no(i)) for pos, i in enumerate(self.ids))
                         if no is not None]
        self.marcados &= {pos for pos, _ in self.visiveis}
        self.cursor = max(0, min(self.cursor, len(self.visiveis) - 1))

    def desenhar_menu(self):
        view = self.app.view
        pares = [("↑ ↓", "Percorrer"), ("ESPAÇO", "Marcar/desmarcar"),
                 ("ENTER", f"{self.verbo} os marcados"), ("ESC", "Voltar para a barra")]
        view.barra()
        for linha in montar_menu_fixo(pares, view.colunas()):
            view.linha(linha, 'dica')

    def render(self):
        view = self.app.view
        largura = view.colunas()
        if self.contexto:
            view.cabecalho(truncar(self.contexto, largura - 2))
        else:
            view.barra()
        n = len(self.marcados)
        view.trechos([(" " + f"{self.verbo} quais itens?", 'nota'),
                      (f"   {n} marcado{'s' if n != 1 else ''}", 'contador')])
        if self._erro:
            view.linha(" " + self._erro, 'erro')
            self._erro = None
        view.barra()
        if not self.visiveis:
            view.linha(" Nenhum item na lista.", 'vazio')
        for i, (pos, no) in enumerate(self.visiveis):
            atual = i == self.cursor
            caixa = MARCA if pos in self.marcados else VAZIO
            prefixo = f" {CURSOR if atual else ' '} {caixa} "
            tag_prefixo = 'flash' if atual else 'numero'
            if self.rotulos is not None:
                view.trechos([(prefixo, tag_prefixo),
                              (truncar(self.rotulos[pos], largura - len(prefixo)), 'nota')])
            else:
                view.trechos(linha_item(pos + 1, no, largura, prefixo=prefixo,
                                        tag_prefixo=tag_prefixo))
        view.barra()
        # rerender (modo_leitura) devolve o foco a barra: aqui ele volta a lista
        view.focar_lista()

    def _repintar(self):
        self.app.rerender()
        # o rerender volta ao topo; o cursor pode estar la embaixo
        if self.visiveis:
            self.app.view.rolar_ate_texto(f" {CURSOR} ")

    # --- teclas da lista ---------------------------------------------------

    def on_tecla_de_lista(self, nome):
        if nome == 'cima':
            self.on_seta(-1)
        elif nome == 'baixo':
            self.on_seta(1)
        elif nome == 'espaco':
            self.marcar()
        elif nome == 'enter':
            self.confirmar()
        else:
            return False
        return True

    def on_seta(self, delta):
        if not self.visiveis:
            return
        self.cursor = max(0, min(len(self.visiveis) - 1, self.cursor + delta))
        self._repintar()

    def marcar(self):
        if not self.visiveis:
            return
        self.marcados ^= {self.visiveis[self.cursor][0]}
        self._repintar()

    def confirmar(self):
        escolhidos = sorted(self.marcados)
        if not escolhidos:
            self._erro = "Marque ao menos um item (ESPAÇO)."
            self._repintar()
            return
        self.app.pop()   # a selecao
        self.app.pop()   # e a pergunta "qual item?" embaixo dela
        self.ao_confirmar(escolhidos)

    # --- barra ---------------------------------------------------------------

    def handle_input(self, texto):
        """ENTER na barra (depois de um clique nela): o foco volta a lista."""
        self.app.rerender()

    def on_cancel(self):
        self.app.pop()

    def on_back(self):
        self.app.pop()
