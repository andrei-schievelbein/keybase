"""Folha de estilo e paleta do Pygments, derivadas de theme.py.

Nao importa Qt: e tudo string, testavel sem display.

Duas decisoes que valem explicacao:

1. O estilo do Pygments e CONSTRUIDO a partir de theme.py, em vez de usar um
   estilo pronto (monokai, friendly). Assim theme.py continua sendo a fonte
   unica das cores, e a hierarquia de tokens do Pygments passa a funcionar
   sozinha - Name.Variable.Instance herda de Name automaticamente.

2. As cores do codigo saem INLINE (noclasses=True), nao como classes CSS. O
   HtmlFormatter gera seletores descendentes (`.codehilite .k`), e o suporte a
   combinadores no rich text do Qt e incerto. Atributo `style=` num `<span>`
   funciona com certeza.
"""

from pygments.style import Style
from pygments.token import (Comment, Keyword, Name, Number, Operator, String,
                            Token)

from ..theme import cores_markdown, cores_tokens

#: Cache: construir a classe Style a cada render seria desperdicio.
_ESTILOS = {}


def estilo_pygments(tema):
    """pygments.style.Style construida a partir das cores do tema."""
    if tema in _ESTILOS:
        return _ESTILOS[tema]

    cores = cores_tokens(tema)
    md = cores_markdown(tema)

    estilo = type(f'KeyBase{tema.title()}', (Style,), {
        'background_color': md['code_bg'],
        'styles': {
            # Base neutra: pontuacao e espaco herdam daqui. Usar code_fg
            # (a cor do codigo inline) pintaria os parenteses de laranja.
            Token: md['texto'],
            Keyword: cores['Keyword'],
            Name: cores['Name'],
            Name.Function: cores['Name.Function'],
            Name.Class: cores['Name.Class'],
            Name.Builtin: cores['Name.Builtin'],
            String: cores['String'],
            Number: cores['Number'],
            Comment: f"italic {cores['Comment']}",
            Operator: cores['Operator'],
        },
    })
    _ESTILOS[tema] = estilo
    return estilo


def folha_de_estilo(tema, fontes):
    """CSS aplicado com QTextDocument.setDefaultStyleSheet().

    Seletores PLANOS de proposito - o rich text do Qt e um subset de CSS 2.1 e
    o suporte a combinadores nao e confiavel.

    Cabecalhos finalmente variam de TAMANHO, nao so de cor: era limitacao do
    CustomTkinter, que nao aceita 'font' em tags por causa do scaling.
    """
    c = cores_markdown(tema)
    base = fontes.get('output_size', 14)
    familia = fontes.get('family', 'monospace')

    return f"""
    body {{ font-family: '{familia}'; font-size: {base}px; color: {c['texto']}; }}

    h1 {{ color: {c['h1']}; font-size: {base + 8}px; font-weight: bold;
          margin-top: 16px; margin-bottom: 6px; }}
    h2 {{ color: {c['h2']}; font-size: {base + 5}px; font-weight: bold;
          margin-top: 14px; margin-bottom: 5px; }}
    h3 {{ color: {c['h3']}; font-size: {base + 3}px; font-weight: bold;
          margin-top: 12px; margin-bottom: 4px; }}
    h4 {{ color: {c['h4']}; font-size: {base + 1}px; font-weight: bold;
          margin-top: 10px; margin-bottom: 3px; }}
    h5, h6 {{ color: {c['h4']}; font-size: {base}px; font-weight: bold;
              margin-top: 8px; margin-bottom: 2px; }}

    p {{ margin-top: 0px; margin-bottom: 10px; }}

    strong, b {{ color: {c['bold']}; font-weight: bold; }}
    em, i {{ color: {c['italic']}; font-style: italic; }}
    del, s {{ color: {c['quote']}; text-decoration: line-through; }}

    code {{ font-family: '{familia}'; background-color: {c['code_bg']};
            color: {c['code_fg']}; }}
    pre {{ font-family: '{familia}'; white-space: pre-wrap; margin: 0px; }}

    blockquote {{ color: {c['quote']}; margin-left: 16px; margin-right: 8px; }}

    ul, ol {{ -qt-list-indent: 1; }}
    ul.task-list {{ list-style-type: none; }}

    table {{ border-collapse: collapse; }}
    th {{ background-color: {c['tabela_cabecalho']}; font-weight: bold; }}

    a {{ color: {c['link']}; text-decoration: underline; }}
    """
