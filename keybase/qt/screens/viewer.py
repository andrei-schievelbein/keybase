"""ViewerScreen: exibe uma nota com o Markdown renderizado."""

from ... import tree
from ...model import File
from ..layout import MARCA_CIFRADA, montar_breadcrumb
from .base import Screen
from .prompt import ConfirmScreen, PromptScreen


class ViewerScreen(Screen):
    COMANDOS = {
        'E': 'cmd_editar',
        'R': 'cmd_renomear',
        'D': 'cmd_deletar',
        'A': 'cmd_abrir',
        'K': 'cmd_cifrar',
        'T': 'cmd_trancar',
        'Y': 'cmd_copiar',
        'U': 'cmd_desfazer',
        'F': 'cmd_favorito',
        'H': 'cmd_historico',
        'L': 'cmd_favoritos',
        'V': 'cmd_voltar',
        'M': 'cmd_raiz',
        'C': 'cmd_config',
    }
    ROTULOS = {
        'E': 'Editar nota', 'R': 'Renomear', 'D': 'Deletar',
        'A': 'Abrir (senha)', 'K': 'Cifrar/decifrar', 'T': 'Trancar/destrancar',
        'Y': 'Área de transferência', 'U': 'Desfazer', 'H': 'Histórico', 'F': 'Favoritar', 'L': 'Favoritos e recentes',
        'V': 'Voltar', 'M': 'Ir para a raiz', 'C': 'Configuração',
    }

    def __init__(self, app, file_id):
        super().__init__(app)
        self.file_id = file_id
        self.file = None
        self.descartada = False
        self._registrado = False  # entra nos recentes uma vez por abertura

    def on_enter(self):
        no = self.app.no(self.file_id)
        if no is None or not isinstance(no, File):
            self.descartada = True
            self.file = None
            return
        self.file = no
        self.descartada = False
        if not self._registrado:
            self.app.registrar_recente(no.id)
            self._registrado = True

    def render(self):
        view = self.app.view
        cadeia = self.app.caminho_de(self.file_id)

        cifrada = self.file is not None and self.file.cifrado
        marca = " " + MARCA_CIFRADA if cifrada else ""
        # o aviso ocupa a linha do caminho por alguns segundos (ver App.flash)
        msg, erro = self.app.consumir_flash()
        if msg:
            view.cabecalho(msg, 'erro' if erro else 'flash')
        else:
            view.cabecalho(montar_breadcrumb(cadeia, view.colunas() - 2 - len(marca))
                           + marca)

        # O cabecalho vai ANTES do markdown. Na versao anterior ele era inserido
        # em "1.0" depois da renderizacao, deslocando as tags ja posicionadas.
        if self.file is not None:
            if self.file.conteudo is None:
                view.linha(" Nota cifrada e trancada. Use A para digitar a senha.",
                           'vazio')
            elif self.file.conteudo.strip():
                from ... import links
                view.markdown(self.file.conteudo,
                              existe=lambda alvo: bool(links.resolver(self.app.raiz, alvo)))
            else:
                view.linha(" Nota vazia. Use E para escrever o conteúdo.", 'vazio')

        view.barra()

    def help_text(self):
        return None

    def comandos_disponiveis(self):
        ativos = set(self.COMANDOS)
        if self.file is None or self.file.conteudo is not None:
            ativos.discard('A')
        if self.app.cofre is None:
            ativos.discard('T')
        if not self.app.pode_desfazer:
            ativos.discard('U')  # nada cifrado ainda: nada a trancar nem destrancar
        return ativos

    def selecionar(self, indice):
        self.app.flash("Esta tela não tem lista. Use E para editar.", erro=True)
        self.app.rerender()

    # --- comandos ----------------------------------------------------------

    def cmd_editar(self, alvo=None):
        from .editor import EditorScreen
        if self.file is not None and self.file.conteudo is None:
            self.app.exigir_cofre(
                lambda: self.app.push(EditorScreen(self.app, self.file_id)))
            return
        self.app.push(EditorScreen(self.app, self.file_id))

    def cmd_abrir(self, alvo=None):
        if self.file is None or self.file.conteudo is not None:
            self.app.rerender()
            return
        self.app.exigir_cofre(self.app.rerender)

    def cmd_cifrar(self, alvo=None):
        if self.file is not None:
            from .browser import alternar_cifra_nota
            alternar_cifra_nota(self.app, self.file)

    def cmd_copiar(self, alvo=None):
        """Y: nota inteira ou a lista de blocos; Y2: o 2o bloco; Y0: a nota."""
        if self.file is None:
            return
        if self.file.conteudo is None:
            self.app.exigir_cofre(lambda: self.cmd_copiar(alvo))
            return
        copiar_da_nota(self.app, self.file, alvo)

    def cmd_historico(self, alvo=None):
        if self.file is None:
            return
        from .historico import HistoricoScreen

        def abrir():
            self.app.push(HistoricoScreen(self.app, self.file_id))

        if self.file.conteudo is None:
            self.app.exigir_cofre(abrir)  # versoes cifradas precisam do cofre
        else:
            abrir()

    def cmd_favorito(self, alvo=None):
        if self.file is not None:
            self.app.alternar_favorito(self.file)

    def cmd_desfazer(self, alvo=None):
        self.app.desfazer()

    def cmd_trancar(self, alvo=None):
        self.app.alternar_tranca()

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
            self.app.registrar_desfazer(f"renomear {self.file.nome!r}")
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
            self.app.registrar_desfazer(f"apagar {nome!r}")
            tree.remover(pai, self.file)
            self.app.persistir()
            self.app.pop()  # sai do viewer: o no nao existe mais
            self.app.flash(f"{nome!r} foi removido.")
            self.app.rerender()

        self.app.push(ConfirmScreen(
            self.app, f"Apagar {tree.resumo_delecao(self.file)}?", aplicar,
        ))


def copiar_da_nota(app, nota, alvo=None):
    """Copia a nota ou um bloco dela. `alvo` e o indice 0-based do bloco;
    -1 (o 'Y0') e a nota inteira; None pergunta, se houver blocos.

    Compartilhado entre o viewer e a listagem (Y3 la copia a nota 3 inteira).
    """
    from ... import blocos as mod_blocos
    from .prompt import PromptScreen

    sensivel = app.item_sensivel(nota)
    blocos = mod_blocos.blocos_de_codigo(nota.conteudo)

    def nota_inteira():
        app.copiar(nota.conteudo, f"nota {nota.nome!r}", sensivel)

    def bloco(i):
        if not (0 <= i < len(blocos)):
            n = len(blocos)
            app.flash(f"A nota tem {n} bloco{'s' if n != 1 else ''} de código." if n
                      else "A nota não tem blocos de código. Use Y para copiar a nota.",
                      erro=True)
            app.rerender()
            return
        nome = blocos[i].linguagem or "texto"
        app.copiar(blocos[i].texto, f"bloco {i + 1} ({nome})", sensivel)

    if alvo == -1 or (alvo is None and not blocos):
        return nota_inteira()
    if alvo is not None:
        return bloco(alvo)

    def escolher(texto):
        numero = int(texto)
        nota_inteira() if numero == 0 else bloco(numero - 1)

    app.push(PromptScreen(
        app, "Copiar o quê?", escolher,
        validar=lambda t: None if t.isdigit() and int(t) <= len(blocos)
        else f"Digite um número de 0 a {len(blocos)}.",
        opcoes=[(0, "A nota inteira")] + [(i, b.rotulo(60))
                                         for i, b in enumerate(blocos, start=1)],
    ))
