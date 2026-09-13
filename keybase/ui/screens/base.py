"""Classe base das telas.

Cada tela junta estado, renderizacao e tratamento de input. Foi o que permitiu
eliminar as seis variaveis globais e os quatro `global` espalhados pelo
despachante de 905 linhas da versao anterior.

O parsing de comando fica aqui, resolvido uma vez so - e por isso que `D3` e
`D` funcionam pelos mesmos caminhos sem codigo duplicado em cada tela.
"""

import re

PADRAO_COMANDO = re.compile(r'^([A-Za-z?])\s*(\d+)?(?:\s+(.*))?$')
PALAVRAS_SAIR = ('sair', 'exit', 'quit')


class Screen:
    #: letra -> nome do metodo que a trata
    COMANDOS = {}
    #: letra -> rotulo curto exibido no rodape
    ROTULOS = {}

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

        if texto.startswith('/'):
            return self.cmd_filtro(texto[1:].strip())

        if texto.isdigit():
            return self.selecionar(int(texto) - 1)

        match = PADRAO_COMANDO.match(texto)
        if match:
            letra, alvo, resto = match.groups()
            letra = letra.upper()
            metodo = self.COMANDOS.get(letra)
            if metodo:
                alvo = int(alvo) - 1 if alvo else None
                return getattr(self, metodo)(alvo=alvo, resto=resto)

        return self.entrada_invalida(texto)

    def entrada_invalida(self, texto):
        self.app.flash("Comando não reconhecido. Digite ? para ver a ajuda.", erro=True)
        self.app.rerender()

    def selecionar(self, indice):
        """Trata um numero digitado. Telas sem lista ignoram."""
        self.entrada_invalida(str(indice + 1))

    def cmd_filtro(self, termo):
        """Trata /termo. Telas sem filtro ignoram."""
        self.entrada_invalida('/' + termo)

    # --- acoes padrao ------------------------------------------------------

    def on_back(self):
        self.app.pop()

    def on_save(self):
        """Ctrl+S. No-op fora do editor."""

    def on_cancel(self):
        """Esc. Por padrao equivale a voltar."""
        self.on_back()

    # --- rodape ------------------------------------------------------------

    def comandos_disponiveis(self):
        """Letras ativas agora. Sobrescreva para esconder o que nao se aplica."""
        return set(self.COMANDOS)

    def desenhar_rodape(self):
        from ..layout import montar_rodape
        linhas = montar_rodape(self.COMANDOS, self.ROTULOS, self.comandos_disponiveis())
        if linhas:
            self.app.view.separador()
            for linha in linhas:
                self.app.view.linha(linha, 'dica')
