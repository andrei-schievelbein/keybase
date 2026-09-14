"""Paletas de cor por tema: markdown, syntax highlighting e cromo da interface.

Na versao anterior as cores dos tokens do Pygments eram fixas no estilo VS Code
Dark, mesmo no tema claro (que e o tema ativo por padrao) - texto claro sobre
fundo claro. Aqui cada tema tem a sua paleta.
"""


def cores_markdown(tema):
    """Cores dos elementos Markdown."""
    if tema == 'dark':
        return {
            'h1': '#569CD6',
            'h2': '#4EC9B0',
            'h3': '#DCDCAA',
            'h4': '#C586C0',
            'bold': '#FFFFFF',
            'italic': '#B4B4B4',
            'code_bg': '#2D2D2D',
            'code_fg': '#CE9178',
            'quote': '#8A8A8A',
            'rule': '#4A4A4A',
        }
    return {
        'h1': '#0066CC',
        'h2': '#008080',
        'h3': '#CC6600',
        'h4': '#8B008B',
        'bold': '#000000',
        'italic': '#404040',
        'code_bg': '#E8E8E8',
        'code_fg': '#8B008B',
        'quote': '#666666',
        'rule': '#C0C0C0',
    }


def cores_tokens(tema):
    """Cores do syntax highlighting, por tipo de token do Pygments."""
    if tema == 'dark':
        return {
            'Keyword': '#569CD6',
            'Name.Function': '#DCDCAA',
            'Name.Class': '#4EC9B0',
            'String': '#CE9178',
            'Number': '#B5CEA8',
            'Comment': '#6A9955',
            'Operator': '#D4D4D4',
            'Name.Builtin': '#4EC9B0',
            'Name': '#9CDCFE',
        }
    # Variante clara: tons escuros o bastante para contrastar com code_bg claro.
    return {
        'Keyword': '#0000CC',
        'Name.Function': '#795E26',
        'Name.Class': '#267F99',
        'String': '#A31515',
        'Number': '#098658',
        'Comment': '#008000',
        'Operator': '#333333',
        'Name.Builtin': '#267F99',
        'Name': '#001080',
    }


def cores_interface(tema):
    """Cromo do terminal: barra de ajuda, breadcrumb, separadores, status."""
    if tema == 'dark':
        return {
            'help_bg': '#1a1a1a',
            'help_fg': 'white',
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
        }
    return {
        'help_bg': '#f0f0f0',
        'help_fg': 'black',
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
    }
