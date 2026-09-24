"""BrowserScreen: a tela de navegacao da arvore.

Uma instancia por nivel, empilhada. A tela guarda o node_id, NUNCA o objeto do
no: se o no some por baixo (deletado noutro ponto da pilha), on_enter percebe e
a tela se auto-descarta em vez de estourar.

INVARIANTE DE NUMERACAO: self.itens e exatamente a lista que foi impressa, e
selecionar e self.itens[n-1]. Nenhum codigo indexa folder.filhos com um numero
digitado - a ordem exibida e derivada e difere da ordem de insercao. Foi esse
descasamento que fez a versao anterior abrir o item errado depois de uma busca.
"""

from ... import cripto, search, tree
from ...model import File, Folder
from ..layout import montar_breadcrumb, truncar
from .base import Screen
from .prompt import ConfirmScreen, PromptScreen


RESPOSTAS_SIM = ('s', 'sim', 'y', 'yes')
RESPOSTAS_NAO = ('', 'n', 'nao', 'não', 'no')


def _validar_sim_nao(texto):
    if texto.lower() in RESPOSTAS_SIM + RESPOSTAS_NAO:
        return None
    return "Responda s (sim) ou n (não)."


class BrowserScreen(Screen):
    COMANDOS = {
        'P': 'cmd_nova_pasta',
        'N': 'cmd_nova_nota',
        'E': 'cmd_editar',
        'R': 'cmd_renomear',
        'D': 'cmd_deletar',
        'B': 'cmd_buscar',
        'K': 'cmd_cifrar',
        'T': 'cmd_trancar',
        'V': 'cmd_voltar',
        'M': 'cmd_raiz',
        'C': 'cmd_config',
    }
    ROTULOS = {
        'P': 'Nova pasta', 'N': 'Nova nota', 'E': 'Editar nota',
        'C': 'Configuração',
        'R': 'Renomear', 'D': 'Deletar', 'B': 'Buscar',
        'K': 'Cifrar/decifrar', 'T': 'Trancar/destrancar',
        'V': 'Voltar', 'M': 'Ir para a raiz',
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
        # pasta cifrada trancada (por T ou por inatividade) com a tela aberta
        # dentro dela: a tela se descarta, como se o no tivesse sumido
        if no is None or not isinstance(no, Folder) or no.trancada:
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
        largura = view.colunas()
        breadcrumb = montar_breadcrumb(cadeia, largura - 2)

        # o aviso ocupa a linha do caminho por alguns segundos (ver App.flash)
        msg, erro = self.app.consumir_flash()
        view.barra()
        if msg:
            view.linha(" " + msg, 'erro' if erro else 'flash')
        elif self.filtro:
            view.trechos([
                (" " + breadcrumb, 'breadcrumb'),
                ("   filtro: ", 'contador'),
                (f'"{self.filtro}"', 'flash'),
            ])
        else:
            view.linha(" " + breadcrumb, 'breadcrumb')
        if not self.filtro and self.folder is not None and self.folder.descricao:
            view.linha(" " + truncar(self.folder.descricao, largura - 2), 'contador')
        view.barra()

        if not self.itens:
            self._render_vazio()
        else:
            for i, no in enumerate(self.itens, start=1):
                view.trechos(linha_item(i, no, largura))

        if self.filtro:
            total = tree.contar_itens(self.folder)
            view.linha(f" {len(self.itens)} de {total} itens - V limpa o filtro",
                       'contador')

        view.barra()

    def _render_vazio(self):
        view = self.app.view
        if self.filtro:
            view.linha(" Nenhum item corresponde ao filtro.", 'vazio')
            return
        view.linha(" Pasta vazia.", 'vazio')
        view.linha(" Use P para criar uma sub-pasta ou N para criar uma nota.", 'dica')

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
            ativos.discard('K')
        if self.app.cofre is None:
            ativos.discard('T')  # nada cifrado ainda: nada a trancar nem destrancar
        return ativos

    # --- navegacao ---------------------------------------------------------

    def selecionar(self, indice):
        no = self._item(indice)
        if no is None:
            return
        if isinstance(no, Folder):
            def entrar():
                self.app.push(BrowserScreen(self.app, no.id))
            if no.trancada:
                self.app.exigir_cofre(entrar)  # destravar abre a pasta
            else:
                entrar()
        else:
            from .viewer import ViewerScreen
            self._com_texto(no, lambda: self.app.push(ViewerScreen(self.app, no.id)))

    def _com_texto(self, nota, acao):
        """Nota cifrada e trancada pede a senha antes; o resto vai direto."""
        if nota.conteudo is None:
            self.app.exigir_cofre(acao)
        else:
            acao()

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

    def cmd_voltar(self, alvo=None):
        self.on_back()

    def cmd_raiz(self, alvo=None):
        if self.na_raiz:
            self.filtro = ""
            self.app.rerender()
            return
        self.app.go_root()

    def cmd_filtro(self, termo):
        self.filtro = termo
        self.app.rerender()

    def cmd_buscar(self, alvo=None):
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

    def cmd_nova_pasta(self, alvo=None):
        def criar(nome, cifrada):
            novo = tree.novo_folder(nome)
            novo.nasce_cifrada = cifrada
            tree.adicionar(self.folder, novo)
            self.app.persistir()
            self.app.flash(f"Pasta {nome!r} criada"
                           + (" - notas novas nascem cifradas." if cifrada else "."))
            self.app.rerender()

        def perguntar_cifra(nome):
            if self.app.pasta_protetora(self.node_id) is not None:
                # dentro de uma pasta cifrada tudo ja e protegido: nem pergunta
                criar(nome, False)
                return

            def responder(texto):
                if texto.lower() in RESPOSTAS_SIM:
                    self.app.garantir_cofre(lambda: criar(nome, True))
                else:
                    criar(nome, False)

            self.app.push(PromptScreen(
                self.app, f"Notas de {nome!r} nascem cifradas? (s/N)", responder,
                validar=_validar_sim_nao, permitir_vazio=True,
                detalhe="ENTER vazio = não. ESC cancela a criação da pasta.",
                contexto=montar_breadcrumb(self.app.caminho_de(self.node_id)),
            ))

        self.app.push(PromptScreen(
            self.app, "Nome da nova pasta:", perguntar_cifra,
            validar=self._validador_nome(),
            contexto=montar_breadcrumb(self.app.caminho_de(self.node_id)),
        ))

    def cmd_nova_nota(self, alvo=None):
        def criar(nome):
            if (cripto.pasta_nasce_cifrada(self.folder)
                    and self.app.pasta_protetora(self.node_id) is None):
                self.app.exigir_cofre(lambda: abrir(nome, cifrada=True))
            else:
                abrir(nome, cifrada=False)

        def abrir(nome, cifrada):
            from .editor import EditorScreen
            from .viewer import ViewerScreen
            nova = tree.novo_file(nome)
            if cifrada:
                cripto.cifrar_nota(self.app.cofre, nova)
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
            itens=list(self.itens),
        ))

    def cmd_editar(self, alvo=None):
        def abrir(no):
            if not isinstance(no, File):
                self.app.flash("Só é possível editar o conteúdo de uma nota.", erro=True)
                self.app.rerender()
                return
            from .editor import EditorScreen
            from .viewer import ViewerScreen

            def editar():
                self.app.stack.append(ViewerScreen(self.app, no.id))
                self.app.push(EditorScreen(self.app, no.id))

            self._com_texto(no, editar)

        self._com_alvo(alvo, "Editar qual nota? (número)", abrir)

    def cmd_renomear(self, alvo=None):
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

    def cmd_deletar(self, alvo=None):
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
                detalhe="Um backup é gravado antes." if forte else "",
                forte=forte,
            ))

        self._com_alvo(alvo, "Deletar qual item? (número)", deletar)

    # --- notas cifradas ----------------------------------------------------

    def cmd_cifrar(self, alvo=None):
        protetora = self.app.pasta_protetora(self.node_id)
        if protetora is not None:
            self.app.flash(f"Tudo aqui já é protegido pela pasta cifrada "
                           f"{protetora.nome!r}.")
            self.app.rerender()
            return

        def alternar(no):
            if isinstance(no, Folder):
                self._cifrar_pasta(no)
            else:
                alternar_cifra_nota(self.app, no)

        self._com_alvo(alvo, "Cifrar ou decifrar qual item? (número)", alternar)

    def _cifrar_pasta(self, pasta):
        if pasta.cifrada:
            self._decifrar_pasta(pasta)
            return
        claras = cripto.notas_em_claro(pasta)
        estado = "sim" if pasta.nasce_cifrada else "não"

        def escolher(texto):
            if texto == '1':
                if not claras:
                    self.app.flash(f"Todas as notas de {pasta.nome!r} já estão cifradas.")
                    self.app.rerender()
                    return
                n = len(claras)
                self.app.push(ConfirmScreen(
                    self.app,
                    f"Cifrar {n} nota{'s' if n != 1 else ''} de {pasta.nome!r}?",
                    lambda: self.app.exigir_cofre(lambda: self.app.cifrar_notas(claras)),
                    detalhe="Inclui as notas das sub-pastas.",
                ))
            elif texto == '2':
                self._alternar_nasce_cifrada(pasta)
            else:
                self.app.push(ConfirmScreen(
                    self.app, f"Cifrar a pasta {pasta.nome!r} inteira?",
                    lambda: self.app.exigir_cofre(
                        lambda: self.app.cifrar_pasta_inteira(pasta)),
                    detalhe="Nomes, sub-pastas e notas passam a exigir a senha; "
                            "só o nome da pasta fica visível.",
                ))

        self.app.push(PromptScreen(
            self.app, f"Pasta {pasta.nome!r}: o que fazer?", escolher,
            validar=lambda t: None if t in ('1', '2', '3') else "Digite 1, 2 ou 3.",
            opcoes=[
                (1, ("Cifrar a nota em claro (inclui sub-pastas)" if len(claras) == 1
                     else f"Cifrar as {len(claras)} notas em claro (inclui sub-pastas)")),
                (2, f"Notas novas nascem cifradas: {estado} -> "
                    f"{'não' if pasta.nasce_cifrada else 'sim'}"),
                (3, "Cifrar a pasta inteira (nomes e sub-pastas incluídos)"),
            ],
            contexto=montar_breadcrumb(self.app.caminho_de(self.node_id)),
        ))

    def _decifrar_pasta(self, pasta):
        def escolher(_texto):
            def confirmar():
                self.app.push(ConfirmScreen(
                    self.app, f"Decifrar a pasta {pasta.nome!r}?",
                    lambda: self.app.decifrar_pasta(pasta),
                    detalhe="Nomes e conteúdo voltam a ficar em claro no arquivo de dados.",
                ))
            self.app.exigir_cofre(confirmar)

        self.app.push(PromptScreen(
            self.app, f"Pasta cifrada {pasta.nome!r}: o que fazer?", escolher,
            validar=lambda t: None if t == '1' else "Digite 1.",
            opcoes=[(1, "Decifrar a pasta (volta a ser uma pasta comum)")],
            contexto=montar_breadcrumb(self.app.caminho_de(self.node_id)),
        ))

    def _alternar_nasce_cifrada(self, pasta):
        def aplicar():
            pasta.nasce_cifrada = not pasta.nasce_cifrada
            pasta.touch()
            self.app.persistir()
            if pasta.nasce_cifrada:
                self.app.flash(f"Notas novas em {pasta.nome!r} nascem cifradas.")
            else:
                self.app.flash(f"Notas novas em {pasta.nome!r} nascem em claro.")
            self.app.rerender()

        if pasta.nasce_cifrada:
            aplicar()
        else:
            self.app.garantir_cofre(aplicar)

    def cmd_trancar(self, alvo=None):
        self.app.alternar_tranca()


def alternar_cifra_nota(app, nota):
    """K sobre uma nota: cifra se esta em claro, decifra (com confirmacao) se nao.

    Compartilhado entre a listagem e o viewer.
    """
    protetora = app.pasta_protetora(nota.id)
    if protetora is not None:
        app.flash(f"Esta nota já é protegida pela pasta cifrada {protetora.nome!r}.")
        app.rerender()
        return
    if not nota.cifrado:
        app.exigir_cofre(lambda: app.cifrar_notas([nota]))
        return

    def decifrar():
        cripto.decifrar_nota(app.cofre, nota)
        app.persistir()
        app.flash(f"Nota {nota.nome!r} decifrada.")
        app.rerender()

    app.exigir_cofre(lambda: app.push(ConfirmScreen(
        app, f"Decifrar a nota {nota.nome!r}?", decifrar,
        detalhe="O conteúdo volta a ficar em claro no arquivo de dados.",
    )))
