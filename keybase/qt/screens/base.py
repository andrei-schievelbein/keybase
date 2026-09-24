"""Classe base das telas.

Cada tela junta estado, renderizacao e tratamento de input. Foi o que permitiu
eliminar as seis variaveis globais e os quatro `global` espalhados pelo
despachante de 905 linhas da versao anterior.

O parsing de comando fica aqui, resolvido uma vez so - e por isso que `D3` e
`D` funcionam pelos mesmos caminhos sem codigo duplicado em cada tela.
"""

import re

# Comando e uma letra, com alvo opcional colado ou separado: 'D', 'D3', 'D 3'.
# Qualquer outra coisa cai no filtro, entao o padrao NAO pode aceitar texto
# solto depois da letra - senao 'd ados' viraria o comando D em vez de filtro.
PADRAO_COMANDO = re.compile(r'^([A-Za-z?])\s*(\d+)?$')
PALAVRAS_SAIR = ('sair', 'exit', 'quit')


class Screen:
    #: letra -> nome do metodo que a trata
    COMANDOS = {}
    #: letra -> rotulo curto exibido no rodape
    ROTULOS = {}
    #: False nas telas que nao desenham o menu (prompts, ajuda, recuperacao,
    #: editor). Uma flag so, consumida pelo desenho E pelo '?'/Ctrl+0: e ela que
    #: garante que o atalho seja inerte exatamente onde o menu nao aparece, em
    #: vez de alternar em silencio um menu que esta fora da tela.
    MOSTRA_MENU = True
    #: True mascara o campo de entrada (prompt de senha). Lido a cada render,
    #: entao nenhuma tela precisa lembrar de desligar a mascara ao sair.
    ENTRADA_SENHA = False

    def __init__(self, app):
        self.app = app

    # --- ciclo de vida -----------------------------------------------------

    def on_enter(self):
        """Recarrega o que a tela precisa. Chamada antes de todo render."""

    def render(self):
        raise NotImplementedError

    def help_text(self):
        """Texto da barra de dica; None a esconde."""
        return None

    def usa_editor(self):
        return False

    # --- input -------------------------------------------------------------

    def handle_input(self, texto):
        texto = (texto or "").strip()

        if texto == "":
            return self.on_back()

        if texto.lower() in PALAVRAS_SAIR:
            return self.app.sair()

        # '?' e '??' sao tratados aqui, e nao por COMANDOS, porque
        # PADRAO_COMANDO casa uma LETRA so - '??' nunca chegaria ao despacho.
        if texto == '??':
            return self.cmd_ajuda_completa()

        if texto == '?':
            return self.on_ajuda()

        if texto.startswith('/'):
            return self.cmd_filtro(texto[1:].strip())

        if texto.isdigit():
            return self.selecionar(int(texto) - 1)

        match = PADRAO_COMANDO.match(texto)
        if match:
            letra, alvo = match.groups()
            letra = letra.upper()
            metodo = self.COMANDOS.get(letra)
            if metodo:
                alvo = int(alvo) - 1 if alvo else None
                return getattr(self, metodo)(alvo=alvo)

        # Nao e comando: o texto filtra o nivel visivel. Cada tela decide o que
        # "filtrar" significa - a de busca global, por exemplo, refaz a busca.
        return self.cmd_filtro(texto)

    def entrada_invalida(self, texto):
        self.app.flash("Comando não reconhecido. Digite ? para ver os comandos "
                       "ou ?? para a ajuda.", erro=True)
        self.app.rerender()

    def selecionar(self, indice):
        """Trata um numero digitado. Telas sem lista ignoram."""
        self.entrada_invalida(str(indice + 1))

    def cmd_filtro(self, termo):
        """Texto livre (ou /termo). Telas sem nada a filtrar avisam.

        E aqui que a recursao para: o fallback de handle_input chama cmd_filtro,
        e quem nao sobrescreve cai neste aviso em vez de voltar ao parsing.
        """
        self.entrada_invalida(termo)

    # --- acoes padrao ------------------------------------------------------

    def on_back(self):
        self.app.pop()

    def on_save(self):
        """Ctrl+S. No-op fora do editor."""

    def on_cancel(self):
        """Esc. Por padrao equivale a voltar."""
        self.on_back()

    def on_modo(self, modo):
        """Ctrl+1/2/3. No-op: so a EditorScreen implementa.

        E por ser no-op aqui que os atalhos de modo sao inertes fora da edicao,
        sem nenhum `if` espalhado pela janela.
        """

    def on_ciclar_modo(self):
        """Ctrl+E. Mesma logica do on_modo."""

    def on_seta(self, delta):
        """Seta na barra. No-op: so as telas com destaque implementam."""

    def on_ajuda(self):
        """'?' na barra ou Ctrl+0: mostra/esconde o menu de comandos."""
        if not self.MOSTRA_MENU:
            return
        self.app.menu_visivel = not self.app.menu_visivel
        self.app.rerender()

    def cmd_favoritos(self, alvo=None):
        """L: favoritos e notas abertas recentemente."""
        from .favoritos import FavoritosScreen
        self.app.push(FavoritosScreen(self.app))

    def cmd_config(self, alvo=None):
        """C: a configuracao aberta no editor, como uma nota."""
        from .config import ConfigScreen
        self.app.push(ConfigScreen(self.app, self.app.caminho_config))

    def cmd_ajuda_completa(self):
        """'??' na barra: a referencia completa."""
        from .help import HelpScreen
        self.app.push(HelpScreen(self.app))

    # --- menu de comandos --------------------------------------------------

    def comandos_disponiveis(self):
        """Letras ativas agora. Sobrescreva para esconder o que nao se aplica."""
        return set(self.COMANDOS)

    #: pares (letra, rotulo) acrescentados ao fim do menu
    EXTRAS = (("??", "Ajuda completa"), ("sair", "Encerrar"))

    def desenhar_menu(self):
        """Menu de comandos: PRIMEIRO bloco da area de leitura, logo abaixo da
        barra de pesquisa. Escondido por padrao - '?' ou Ctrl+0 o alterna.

        Nao emite a barra de baixo: quem fecha o bloco e a barra de abertura da
        propria tela, que de outro modo apareceria duplicada.
        """
        if not (self.MOSTRA_MENU and self.app.menu_visivel):
            return

        from ..layout import montar_menu
        view = self.app.view
        linhas = montar_menu(self.COMANDOS, self.ROTULOS,
                             self.comandos_disponiveis(),
                             largura=view.colunas(),
                             extras=self.EXTRAS)
        if not linhas:
            return

        view.barra()
        for linha in linhas:
            view.linha(linha, 'dica')
