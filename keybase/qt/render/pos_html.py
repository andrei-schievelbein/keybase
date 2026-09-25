"""Correcoes no HTML para o subset de rich text do Qt.

O QTextDocument implementa HTML 4 + CSS 2.1 parcial, nao um motor de
navegador. Tres coisas que o markdown gera simplesmente nao aparecem:

- `<input type="checkbox">` das listas de tarefa e DESCARTADO em silencio,
  deixando o item sem marcador nenhum -> vira ☑/☐
- `<table>` sem atributos renderiza SEM grade, o que torna a tabela ilegivel
  -> ganha border/cellpadding/cellspacing
- `padding` nao funciona em bloco, so em celula de tabela, entao um `<pre>` com
  fundo fica com o texto colado na borda -> o bloco de codigo e envolvido numa
  tabela de uma celula com cellpadding

As correcoes acontecem em DUAS etapas, e a divisao nao e arbitraria:

- `AjustesParaQt` (Treeprocessor) trata tabelas e imagens, que estao na arvore
- `AjustesFinais` (Postprocessor) trata blocos de codigo e caixas de tarefa,
  que NAO estao na arvore: o superfences e o tasklist guardam esse HTML no
  htmlStash como placeholder (`wzxhzdk:N`) e so o `raw_html`, um postprocessor,
  substitui pelo conteudo real. Um Treeprocessor ve so o placeholder.

Nao importa Qt.
"""

import html
import re

from markdown.postprocessors import Postprocessor
from markdown.treeprocessors import Treeprocessor
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_by_name
from pygments.util import ClassNotFound

from .estilo import estilo_pygments

# Sem espaco: o HTML do tasklist ja traz um depois do <input>.
CAIXA_MARCADA = '☑'
CAIXA_VAZIA = '☐'

RE_PROTOCOLO_REMOTO = re.compile(r'^(https?|ftp)://', re.IGNORECASE)

RE_BLOCO_CODIGO = re.compile(
    r'<pre[^>]*>\s*<code([^>]*)>(.*?)</code>\s*</pre>',
    re.DOTALL,
)
RE_LINGUAGEM = re.compile(r'(?:language-|lang-)([\w+#.-]+)')
RE_CHECKBOX = re.compile(r'<input[^>]*type="checkbox"[^>]*>')


def realcar(codigo, linguagem, tema):
    """Codigo -> spans coloridos com estilo inline. Nunca levanta."""
    try:
        if linguagem:
            try:
                lexer = get_lexer_by_name(linguagem.lower(), stripall=False)
            except ClassNotFound:
                lexer = TextLexer()
        else:
            lexer = TextLexer()

        formatador = HtmlFormatter(
            style=estilo_pygments(tema),
            noclasses=True,   # style= inline; ver docstring de estilo.py
            nowrap=True,      # sem <div><pre>: o involucro e nosso
        )
        return highlight(codigo, lexer, formatador).rstrip('\n')
    except Exception:
        return html.escape(codigo)


class AjustesParaQt(Treeprocessor):
    """Correcoes que cabem na arvore: tabelas e imagens."""

    def __init__(self, md, tema, cores):
        super().__init__(md)
        self.tema = tema
        self.cores = cores

    def run(self, raiz):
        self._tabelas(raiz)
        self._imagens_remotas(raiz)
        return raiz

    def _tabelas(self, raiz):
        """Tabela sem atributos renderiza sem grade nenhuma no Qt."""
        for tabela in raiz.iter('table'):
            tabela.set('border', '1')
            tabela.set('cellpadding', '4')
            tabela.set('cellspacing', '0')
            tabela.set('bordercolor', self.cores['tabela_borda'])

    def _imagens_remotas(self, raiz):
        """O QTextBrowser nao tem loader de rede: imagem http vira link.

        Melhor um link legivel que um icone de imagem quebrada.
        """
        from xml.etree import ElementTree as ET
        for pai in raiz.iter():
            for i, elemento in enumerate(list(pai)):
                if elemento.tag != 'img':
                    continue
                src = elemento.get('src', '')
                if not RE_PROTOCOLO_REMOTO.match(src):
                    continue
                link = ET.Element('a', {'href': src})
                link.text = elemento.get('alt') or src
                link.tail = elemento.tail
                pai.remove(elemento)
                pai.insert(i, link)


class AjustesFinais(Postprocessor):
    """Correcoes que so existem depois do htmlStash ser resolvido.

    Prioridade abaixo de `raw_html` (30) para rodar com o HTML real em maos, e
    abaixo de `amp_substitute` (20) para que o conteudo inserido aqui nao seja
    reprocessado.
    """

    def __init__(self, md, tema, cores):
        super().__init__(md)
        self.tema = tema
        self.cores = cores

    def run(self, texto):
        texto = RE_BLOCO_CODIGO.sub(self._bloco, texto)
        texto = self._tarefas(texto)
        return texto

    def _bloco(self, casamento):
        atributos, corpo = casamento.group(1), casamento.group(2)
        achado = RE_LINGUAGEM.search(atributos or '')
        linguagem = achado.group(1) if achado else ''

        # o corpo vem escapado; o Pygments escapa de novo ao formatar
        codigo = html.unescape(corpo).rstrip('\n')
        realcado = realcar(codigo, linguagem, self.tema)

        # A tabela existe porque `padding` nao vale em bloco no Qt; cellpadding
        # e atributo HTML e e honrado, entao o fundo ganha respiro.
        return (
            f'<table class="codigo" width="100%" cellpadding="8" '
            f'cellspacing="0" border="0" bgcolor="{self.cores["code_bg"]}">'
            f'<tr><td><pre>{realcado}</pre></td></tr></table>'
        )

    def _tarefas(self, texto):
        """<input type=checkbox> some no Qt; vira ☑/☐ antes do rotulo."""
        def trocar(casamento):
            marcada = 'checked' in casamento.group(0)
            return CAIXA_MARCADA if marcada else CAIXA_VAZIA
        return RE_CHECKBOX.sub(trocar, texto)
