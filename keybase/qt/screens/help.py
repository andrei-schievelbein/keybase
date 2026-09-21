"""HelpScreen: referencia de comandos."""

from .. import atalhos
from .base import Screen

SECOES = [
    ("Navegação", [
        ("1 2 3 …", "abrir o item pelo número da lista"),
        ("V", "voltar um nível (ou limpar o filtro)"),
        ("M", "ir direto para a raiz"),
        ("Enter vazio", "o mesmo que V"),
    ]),
    ("Criar e editar", [
        ("C", "criar uma pasta na pasta atual"),
        ("N", "criar uma nota na pasta atual"),
        ("E  ou  E3", "editar o conteúdo de uma nota"),
        ("R  ou  R3", "renomear um item"),
        ("D  ou  D3", "apagar um item"),
    ]),
    ("Buscar", [
        ("texto", "filtrar a pasta atual pelo nome - basta digitar e dar Enter"),
        ("/texto", "o mesmo, para termos que colidem com um comando (/b, /c)"),
        ("B", "buscar em toda a base (nome, descrição e conteúdo)"),
        ("V", "limpa o filtro e volta a listar tudo"),
    ]),
    ("No editor de notas", [
        (atalhos.rotulo(atalhos.SALVAR), "salvar e voltar"),
        (atalhos.rotulo(atalhos.CANCELAR), "cancelar (pergunta antes de descartar)"),
        (atalhos.rotulo(atalhos.MODO_EDITAR), "só o editor"),
        (atalhos.rotulo(atalhos.MODO_PREVIEW), "só o preview (do texto não salvo)"),
        (atalhos.rotulo(atalhos.MODO_DIVIDIDO), "tela dividida: editor e preview"),
        (atalhos.rotulo(atalhos.MODO_CICLAR), "alterna entre os três modos"),
        ("```python", "abre um bloco de código com destaque de sintaxe"),
    ]),
    ("Outros", [
        ("?", "mostra ou esconde o menu de comandos"),
        (atalhos.rotulo(atalhos.AJUDA_DINAMICA), "o mesmo que ?"),
        ("??", "esta ajuda completa"),
        ("sair", "encerrar (a janela também salva ao fechar)"),
    ]),
]


class HelpScreen(Screen):
    COMANDOS = {'V': 'cmd_voltar'}
    ROTULOS = {'V': 'Voltar'}
    # Esta tela ja lista tudo: nao desenha o menu, e o '?'/Ctrl+0 fica inerte.
    MOSTRA_MENU = False

    def render(self):
        view = self.app.view
        view.cabecalho("AJUDA - COMANDOS DO KEYBASE")

        for titulo, linhas in SECOES:
            view.linha(" " + titulo.upper(), 'pasta')
            for comando, descricao in linhas:
                view.trechos([
                    (f" {comando:>13} - ", 'flash'),
                    (descricao, 'nota'),
                ])
            view.linha()

        view.barra()
        view.linha(" Uma pasta pode conter outras pastas e notas, sem limite de "
                   "profundidade.", 'dica')
        view.linha(" Notas são escritas em Markdown.", 'dica')
        view.barra()
        view.linha(" V ou ENTER para voltar", 'dica')
        view.barra()

    def selecionar(self, indice):
        self.app.pop()

    def cmd_voltar(self, alvo=None):
        self.app.pop()

    def cmd_ajuda_completa(self):
        """Evita empilhar uma segunda HelpScreen, identica, sobre esta - o 'V'
        de volta precisaria ser apertado duas vezes sem nada explicar por que."""
