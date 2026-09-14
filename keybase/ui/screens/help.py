"""HelpScreen: referencia de comandos."""

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
        ("B", "buscar em toda a base (nome, descrição e conteúdo)"),
        ("/termo", "filtrar só a pasta atual, sem sair dela"),
    ]),
    ("No editor de notas", [
        ("Ctrl+S", "salvar e voltar"),
        ("Esc", "cancelar (pergunta antes de descartar)"),
        ("```python", "abre um bloco de código com destaque de sintaxe"),
    ]),
    ("Outros", [
        ("?", "esta ajuda"),
        ("sair", "encerrar (a janela também salva ao fechar)"),
    ]),
]


class HelpScreen(Screen):
    COMANDOS = {'V': 'cmd_voltar'}
    ROTULOS = {'V': 'Voltar'}

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

    def cmd_voltar(self, alvo=None, resto=None):
        self.app.pop()

    def desenhar_rodape(self):
        pass
