"""Paletas de cor por tema. Fonte da verdade das cores do app.

As chaves de `cores_interface` sao os nomes das tags usadas pelas telas
(`linha(texto, 'pasta')`), mais o cromo da janela.

Diferenca em relacao ao CustomTkinter: la o fundo da janela vinha de graca do
framework. Em Qt ele tem que ser declarado aqui, senao um trecho escrito sem
tag fica com a cor do sistema e some no tema escuro.
"""


def cores_markdown(tema):
    """Cores dos elementos Markdown no preview."""
    if tema == 'dark':
        return {
            'h1': '#569CD6',
            'h2': '#4EC9B0',
            'h3': '#DCDCAA',
            'h4': '#C586C0',
            'texto': '#D4D4D4',
            'bold': '#FFFFFF',
            'italic': '#B4B4B4',
            'code_bg': '#333333',
            'code_fg': '#CE9178',
            'quote': '#8A8A8A',
            'quote_borda': '#4A4A4A',
            'rule': '#4A4A4A',
            'link': '#4EC9B0',
            'tabela_borda': '#4A4A4A',
            'tabela_cabecalho': '#2D2D2D',
        }
    return {
        'h1': '#0066CC',
        'h2': '#008080',
        'h3': '#B35900',
        'h4': '#8B008B',
        'texto': '#1E1E1E',
        'bold': '#000000',
        'italic': '#404040',
        'code_bg': '#F0F0F0',
        'code_fg': '#8B008B',
        'quote': '#666666',
        'quote_borda': '#C0C0C0',
        'rule': '#C0C0C0',
        'link': '#006699',
        'tabela_borda': '#C0C0C0',
        'tabela_cabecalho': '#EFEFEF',
    }


def cores_interface(tema):
    """Cromo do terminal e da janela.

    As dez primeiras chaves sao as tags que as telas usam ao escrever.
    As quatro ultimas sao da janela e nao existiam na versao CustomTkinter.
    """
    if tema == 'dark':
        return {
            # tags de conteudo
            'breadcrumb': '#4EC9B0',
            'separador': '#7A7A7A',
            'numero': '#858585',
            'pasta': '#569CD6',
            'nota': '#D4D4D4',
            'contador': '#858585',
            'dica': '#858585',
            'flash': '#4EC9B0',
            'erro': '#F48771',
            'vazio': '#858585',
            # barra de ajuda
            'help_bg': '#1A1A1A',
            'help_fg': '#D4D4D4',
            # janela
            'fundo': '#1E1E1E',
            'texto': '#D4D4D4',
            'entrada_bg': '#2D2D2D',
            'entrada_borda': '#3F3F3F',
            'selecao': '#264F78',
            'selecao_texto': '#FFFFFF',
        }
    return {
        'breadcrumb': '#008080',
        'separador': '#8A8A8A',
        'numero': '#767676',
        'pasta': '#0066CC',
        'nota': '#1E1E1E',
        'contador': '#767676',
        'dica': '#767676',
        'flash': '#008080',
        'erro': '#C0392B',
        'vazio': '#767676',
        'help_bg': '#F0F0F0',
        'help_fg': '#1E1E1E',
        'fundo': '#FFFFFF',
        'texto': '#1E1E1E',
        'entrada_bg': '#F7F7F7',
        'entrada_borda': '#C8C8C8',
        'selecao': '#ADD6FF',
        'selecao_texto': '#000000',
    }


def cores_tokens(tema):
    """Cores do syntax highlighting, por tipo de token do Pygments.

    Viram uma pygments.style.Style em render/estilo.py, o que faz a hierarquia
    de tokens funcionar sozinha: Name.Variable.Instance herda de Name sem
    precisar estar aqui. Na versao anterior isso era um hack de
    `str(tipo).split('.')[-1]` que deixava muitos tokens sem cor.
    """
    if tema == 'dark':
        return {
            'Keyword': '#569CD6',
            'Name': '#9CDCFE',
            'Name.Function': '#DCDCAA',
            'Name.Class': '#4EC9B0',
            'Name.Builtin': '#4EC9B0',
            'String': '#CE9178',
            'Number': '#B5CEA8',
            'Comment': '#6A9955',
            'Operator': '#D4D4D4',
        }
    return {
        'Keyword': '#0000CC',
        'Name': '#001080',
        'Name.Function': '#795E26',
        'Name.Class': '#267F99',
        'Name.Builtin': '#267F99',
        'String': '#A31515',
        'Number': '#098658',
        'Comment': '#008000',
        'Operator': '#333333',
    }


#: Espacamento vertical de cada tag, em pixels: (acima, abaixo).
#: Herdado dos `spacing1`/`spacing3` das tags do Tk.
ESPACAMENTO = {
    'breadcrumb': (4, 4),
    'dica': (4, 0),
    'flash': (4, 0),
    'erro': (4, 0),
    'vazio': (6, 6),
}


#: Estilo do Pygments usado no syntax highlighting do preview, por tema.
ESTILO_PYGMENTS = {'dark': 'monokai', 'light': 'friendly'}
