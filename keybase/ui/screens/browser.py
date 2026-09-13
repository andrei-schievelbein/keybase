"""BrowserScreen: a tela de navegacao da arvore.

Uma instancia por nivel, empilhada. A tela guarda o node_id, NUNCA o objeto do
no: se o no some por baixo (deletado noutro ponto da pilha), on_enter percebe e
a tela se auto-descarta em vez de estourar.

INVARIANTE DE NUMERACAO: self.itens e exatamente a lista que foi impressa, e
selecionar e self.itens[n-1]. Nenhum codigo indexa folder.filhos com um numero
digitado - a ordem exibida e derivada e difere da ordem de insercao. Foi esse
descasamento que fez a versao anterior abrir o item errado depois de uma busca.
"""

from ... import search, tree
from ...model import File, Folder
from ..layout import montar_breadcrumb
from .base import Screen
from .prompt import ConfirmScreen, PromptScreen


class BrowserScreen(Screen):
    COMANDOS = {
        'C': 'cmd_nova_pasta',
        'N': 'cmd_nova_nota',
        'E': 'cmd_editar',
        'R': 'cmd_renomear',
        'D': 'cmd_deletar',
        'B': 'cmd_buscar',
        'V': 'cmd_voltar',
        'M': 'cmd_raiz',
        '?': 'cmd_ajuda',
    }
    ROTULOS = {
        'C': 'pasta', 'N': 'nota', 'E': 'editar', 'R': 'renomear',
        'D': 'deletar', 'B': 'buscar', 'V': 'voltar', 'M': 'raiz',
        '?': 'ajuda',
    }

    def __init__(self, app, node_id):
        super().__init__(app)
        self.node_id = node_id
        self.filtro = ""
        self.itens = []
        self.folder = None
        self.descartada = False

    # --- ciclo de vida -----------------------------------------------------

    def on_enter(self):
        no = self.app.no(self.node_id)
        if no is None or not isinstance(no, Folder):
            self.descartada = True
            self.folder = None
            self.itens = []
            return
        self.folder = no
        self.descartada = False

        if self.filtro:
            filtrados = search.filtrar(self.folder, self.filtro)
            self.itens = filtrados if filtrados is not None else []
        else:
            self.itens = tree.filhos_ordenados(self.folder)

    @property
    def na_raiz(self):
        return self.app.pai_de(self.node_id) is None

    # --- render ------------------------------------------------------------

    def render(self):
        from ..layout import linha_item
        view = self.app.view

        cadeia = self.app.caminho_de(self.node_id)
        breadcrumb = montar_breadcrumb(cadeia)
        if self.filtro:
            view.trechos([
                (breadcrumb, 'breadcrumb'),
                ("    filtro: ", 'contador'),
                (f'"{self.filtro}"', 'flash'),
            ])
        else:
            view.linha(breadcrumb, 'breadcrumb')

        if self.folder is not None and self.folder.descricao and not self.filtro:
            view.linha("  " + self.folder.descricao, 'contador')

        view.separador()

        msg, erro = self.app.consumir_flash()
        if msg:
            view.linha("  " + msg, 'erro' if erro else 'flash')
            view.linha()

        if not self.itens:
            self._render_vazio()
        else:
            for i, no in enumerate(self.itens, start=1):
                view.trechos(linha_item(i, no))

        if self.filtro:
            total = tree.contar_itens(self.folder)
            view.linha()
            view.linha(f"  {len(self.itens)} de {total} itens   ·   V limpa o filtro",
                       'contador')

        self.desenhar_rodape()

    def _render_vazio(self):
        view = self.app.view
        if self.filtro:
            view.linha("  (nenhum item corresponde ao filtro)", 'vazio')
            return
        view.linha("  (pasta vazia)", 'vazio')
        view.linha()
        view.linha("   C  criar uma sub-pasta aqui", 'dica')
        view.linha("   N  criar uma nota aqui", 'dica')

    def help_text(self):
        return None

    def comandos_disponiveis(self):
        ativos = set(self.COMANDOS)
        if self.na_raiz and not self.filtro:
            ativos.discard('V')
            ativos.discard('M')
        if not any(isinstance(n, File) for n in self.itens):
            ativos.discard('E')
        if not self.itens:
            ativos.discard('R')
            ativos.discard('D')
            ativos.discard('E')
        return ativos

    # --- navegacao ---------------------------------------------------------

    def selecionar(self, indice):
        no = self._item(indice)
        if no is None:
            return
        if isinstance(no, Folder):
            self.app.push(BrowserScreen(self.app, no.id))
        else:
            from .viewer import ViewerScreen
            self.app.push(ViewerScreen(self.app, no.id))

    def _item(self, indice):
        """Resolve um numero contra a lista EXIBIDA. Ver invariante no topo."""
        if indice is None or not (0 <= indice < len(self.itens)):
            self.app.flash("Número fora da lista.", erro=True)
            self.app.rerender()
            return None
        return self.itens[indice]

    def on_back(self):
        if self.filtro:
            self.filtro = ""
            self.app.rerender()
            return
        if self.na_raiz:
            self.app.flash("Você já está na raiz. Digite 'sair' para encerrar.")
            self.app.rerender()
            return
        self.app.pop()

    def cmd_voltar(self, alvo=None, resto=None):
        self.on_back()

    def cmd_raiz(self, alvo=None, resto=None):
        if self.na_raiz:
            self.filtro = ""
            self.app.rerender()
            return
        self.app.go_root()

    def cmd_filtro(self, termo):
        self.filtro = termo
        self.app.rerender()

    def cmd_ajuda(self, alvo=None, resto=None):
        from .help import HelpScreen
        self.app.push(HelpScreen(self.app))

    def cmd_buscar(self, alvo=None, resto=None):
        from .search import SearchResultsScreen

        def abrir(termo):
            self.app.push(SearchResultsScreen(self.app, termo))

        self.app.push(PromptScreen(
            self.app,
            "Buscar em toda a base:",
            abrir,
            contexto=montar_breadcrumb(self.app.caminho_de(self.node_id)),
        ))

    # --- criacao -----------------------------------------------------------

    def _validador_nome(self, ignorar=None):
        def validar(nome):
            if not nome:
                return "O nome não pode ficar vazio."
            if not tree.nome_disponivel(self.folder, nome, ignorar=ignorar):
                return f"Já existe um item chamado {nome!r} nesta pasta."
            return None
        return validar

    def cmd_nova_pasta(self, alvo=None, resto=None):
        def criar(nome):
            novo = tree.novo_folder(nome)
            tree.adicionar(self.folder, novo)
            self.app.persistir()
            self.app.flash(f"Pasta {nome!r} criada.")
            self.app.rerender()

        self.app.push(PromptScreen(
            self.app, "Nome da nova pasta:", criar,
            validar=self._validador_nome(),
            contexto=montar_breadcrumb(self.app.caminho_de(self.node_id)),
        ))

    def cmd_nova_nota(self, alvo=None, resto=None):
        def criar(nome):
            from .editor import EditorScreen
            from .viewer import ViewerScreen
            nova = tree.novo_file(nome)
            tree.adicionar(self.folder, nova)
            self.app.persistir()
            # cai direto no editor, com o viewer embaixo: sair do editor sempre
            # volta para o viewer, uma regra so
            self.app.stack.append(ViewerScreen(self.app, nova.id))
            self.app.push(EditorScreen(self.app, nova.id))

        self.app.push(PromptScreen(
            self.app, "Nome da nova nota:", criar,
            validar=self._validador_nome(),
            contexto=montar_breadcrumb(self.app.caminho_de(self.node_id)),
        ))

    # --- comandos com alvo -------------------------------------------------

    def _com_alvo(self, alvo, pergunta, acao, filtro=None):
        """Aceita `D3` (alvo direto) e `D` (pergunta o numero).

        O parsing ja veio pronto da classe base; aqui so falta o caso sem alvo.
        """
        if alvo is not None:
            no = self._item(alvo)
            if no is not None:
                acao(no)
            return

        if not self.itens:
            self.app.flash("Não há itens nesta pasta.", erro=True)
            self.app.rerender()
            return

        def escolher(texto):
            if not texto.isdigit():
                self.app.flash("Digite o número do item.", erro=True)
                self.app.rerender()
                return
            no = self._item(int(texto) - 1)
            if no is not None:
                acao(no)

        self.app.push(PromptScreen(
            self.app, pergunta, escolher,
            contexto=montar_breadcrumb(self.app.caminho_de(self.node_id)),
        ))

    def cmd_editar(self, alvo=None, resto=None):
        def abrir(no):
            if not isinstance(no, File):
                self.app.flash("Só é possível editar o conteúdo de uma nota.", erro=True)
                self.app.rerender()
                return
            from .editor import EditorScreen
            from .viewer import ViewerScreen
            self.app.stack.append(ViewerScreen(self.app, no.id))
            self.app.push(EditorScreen(self.app, no.id))

        self._com_alvo(alvo, "Editar qual nota? (número)", abrir)

    def cmd_renomear(self, alvo=None, resto=None):
        def renomear(no):
            def aplicar(nome):
                tree.renomear(no, nome)
                self.app.persistir()
                self.app.flash(f"Renomeado para {nome!r}.")
                self.app.rerender()

            self.app.push(PromptScreen(
                self.app, f"Novo nome para {no.nome!r}:", aplicar,
                valor_inicial=no.nome,
                validar=self._validador_nome(ignorar=no),
                contexto=montar_breadcrumb(self.app.caminho_de(self.node_id)),
            ))

        self._com_alvo(alvo, "Renomear qual item? (número)", renomear)

    def cmd_deletar(self, alvo=None, resto=None):
        def deletar(no):
            def aplicar():
                self.app.snapshot()  # o backup e o 'undo' real
                tree.remover(self.folder, no)
                self.app.persistir()
                self.app.flash(f"{no.nome!r} foi removido.")
                self.app.rerender()

            forte = tree.precisa_confirmacao_forte(no)
            self.app.push(ConfirmScreen(
                self.app,
                f"Apagar {tree.resumo_delecao(no)}?",
                aplicar,
                detalhe="Esta ação não pode ser desfeita pelo app, mas um backup "
                        "é gravado antes." if forte else "",
                forte=forte,
            ))

        self._com_alvo(alvo, "Deletar qual item? (número)", deletar)
