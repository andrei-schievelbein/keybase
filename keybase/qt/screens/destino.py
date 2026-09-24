"""DestinoScreen: escolher a pasta para onde mover (X) ou copiar (Y) um item.

Uma tela so, que navega por dentro: o numero entra numa sub-pasta, Enter
vazio sobe, M vai a raiz e C confirma (move ou copia) para a pasta mostrada. Empilhar uma tela
por nivel, como o browser faz, obrigaria o cancelamento a desempilhar N telas.

So pastas aparecem, e nunca o proprio item movido: entrar nele seria o unico
jeito de pedir um ciclo, e tree.mover recusaria de qualquer forma.
"""

from ... import cripto, tree
from ...model import Folder
from ..layout import linha_item, montar_breadcrumb, truncar
from .base import Screen
from .prompt import ConfirmScreen


class DestinoScreen(Screen):
    COMANDOS = {'C': 'cmd_confirmar', 'V': 'cmd_voltar', 'M': 'cmd_raiz'}
    ROTULOS = {'C': 'Confirmar', 'V': 'Subir um nível', 'M': 'Ir para a raiz'}
    MOSTRA_MENU = False  # as instrucoes ja estao na tela

    def __init__(self, app, no_id, pasta_id, copiar=False):
        super().__init__(app)
        #: copiar = mover sem tirar da origem (Y na lista)
        self.copiar = copiar
        self.no_id = no_id
        self.pasta_id = pasta_id
        self.no = None
        self.pasta = None
        self.itens = []
        self.descartada = False

    def on_enter(self):
        self.no = self.app.no(self.no_id)
        if self.no is None:
            self.descartada = True
            return
        pasta = self.app.no(self.pasta_id)
        # a pasta mostrada sumiu ou trancou (T, inatividade): volta para a raiz
        if pasta is None or not isinstance(pasta, Folder) or pasta.trancada:
            pasta = self.app.raiz
            self.pasta_id = pasta.id
        self.pasta = pasta
        self.itens = [f for f in tree.filhos_ordenados(pasta)
                      if isinstance(f, Folder) and f is not self.no]

    def render(self):
        view = self.app.view
        largura = view.colunas()
        caminho = montar_breadcrumb(self.app.caminho_de(self.pasta_id), largura - 2)

        view.barra()
        verbo = "Copiar" if self.copiar else "Mover"
        view.linha(" " + truncar(f"{verbo} {self.no.nome!r} para:", largura - 2), 'nota')
        msg, erro = self.app.consumir_flash()
        if msg:
            view.linha(" " + msg, 'erro' if erro else 'flash')
        else:
            view.linha(" " + caminho, 'breadcrumb')
        view.barra()
        view.trechos([(" C - ", 'numero'), (f"{verbo} para esta pasta", 'nota')])
        view.barra()
        if self.itens:
            for i, pasta in enumerate(self.itens, start=1):
                view.trechos(linha_item(i, pasta, largura))
        else:
            view.linha(" Nenhuma sub-pasta aqui.", 'vazio')
        view.barra()
        acao = "copia" if self.copiar else "move"
        view.linha(f" Número entra na pasta | C {acao} para cá | ENTER sobe | "
                   "M raiz | ESC cancela", 'dica')
        view.barra()

    # --- navegacao ---------------------------------------------------------

    def selecionar(self, indice):
        if not (0 <= indice < len(self.itens)):
            self.app.flash("Número fora da lista.", erro=True)
            self.app.rerender()
            return
        pasta = self.itens[indice]

        def entrar():
            self.pasta_id = pasta.id
            self.app.rerender()

        if pasta.trancada:
            self.app.exigir_cofre(entrar)
        else:
            entrar()

    def on_back(self):
        pai = self.app.pai_de(self.pasta_id)
        if pai is None:
            self.app.pop()  # Enter vazio na raiz: desiste
            return
        self.pasta_id = pai.id
        self.app.rerender()

    def on_cancel(self):
        self.app.pop()

    def cmd_voltar(self, alvo=None):
        self.on_back()

    def cmd_raiz(self, alvo=None):
        self.pasta_id = self.app.raiz.id
        self.app.rerender()

    def cmd_confirmar(self, alvo=None):
        self.confirmar()

    # --- mover ---------------------------------------------------------------

    def confirmar(self):
        if self.copiar:
            return self._confirmar_copia()
        no, destino = self.no, self.pasta
        origem = self.app.pai_de(no.id)
        if destino is origem:
            self.app.flash(f"{no.nome!r} já está nesta pasta.", erro=True)
            self.app.rerender()
            return
        if not tree.nome_disponivel(destino, no.nome):
            self.app.flash(f"Já existe um item chamado {no.nome!r} nesta pasta.", erro=True)
            self.app.rerender()
            return

        protege_origem = self.app.pasta_protetora(origem.id)
        protege_destino = self.app.pasta_protetora(destino.id)
        caminho = montar_breadcrumb(self.app.caminho_de(destino.id))

        def aplicar():
            self.app.snapshot()
            self.app.registrar_desfazer(f"mover {no.nome!r}")
            if protege_destino is not None:
                cripto.absorver_em_pasta_cifrada(self.app.cofre, no)
            try:
                tree.mover(no, origem, destino)
            except tree.CicloError as e:
                self.app.cancelar_desfazer()
                self.app.flash(str(e), erro=True)
                self.app.rerender()
                return
            self.app.persistir()
            if self.app.atual is self:
                self.app.pop()
            self.app.flash(f"{no.nome!r} movido para {caminho}.")
            self.app.rerender()

        if protege_origem is not None and protege_destino is None:
            # sair de uma pasta cifrada deixa o item em claro no arquivo
            self.app.push(ConfirmScreen(
                self.app, f"{no.nome!r} sai da pasta cifrada {protege_origem.nome!r}. Mover?",
                aplicar,
                detalhe="Fora dela, o conteúdo fica em claro no arquivo de dados."))
            return
        aplicar()

    def _confirmar_copia(self):
        no, destino = self.no, self.pasta
        protege_origem = self.app.pasta_protetora(no.id)
        protege_destino = self.app.pasta_protetora(destino.id)

        def fechar():
            if self.app.atual is self:
                self.app.pop()

        def aplicar():
            self.app.copiar_para(no, destino, depois=fechar)

        if protege_origem is not None and protege_destino is None:
            # a copia fora da pasta cifrada fica em claro no arquivo
            self.app.push(ConfirmScreen(
                self.app, f"A cópia de {no.nome!r} fica fora da pasta cifrada "
                          f"{protege_origem.nome!r}. Copiar?",
                aplicar,
                detalhe="Fora dela, o conteúdo da cópia fica em claro no arquivo de dados."))
            return
        aplicar()
