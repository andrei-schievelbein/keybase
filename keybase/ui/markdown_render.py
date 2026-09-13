"""Renderizacao de Markdown num CTkTextbox, com syntax highlighting.

Preservado da versao anterior, com tres mudancas:
- o parser recebe `cores` no construtor, em vez de ler uma config global
- os imports do Pygments sobem para o topo do modulo
- handle_data nao descarta mais texto cujo strip() e vazio, o que colava
  palavras vizinhas quando havia formatacao inline no meio da frase

Limitacao herdada: CustomTkinter nao aceita 'font' em tags por causa do
scaling, entao os cabecalhos se distinguem por cor e espacamento, nao por
tamanho.
"""

from html.parser import HTMLParser

import markdown
from pygments import lex
from pygments.lexers import TextLexer, get_lexer_by_name
from pygments.util import ClassNotFound

TAGS_MARKDOWN = ('h1', 'h2', 'h3', 'h4', 'bold', 'italic', 'code',
                 'code_block', 'list', 'quote')


class HTMLToTkinterParser(HTMLParser):
    """Converte o HTML gerado pelo modulo markdown em texto com tags do Tk."""

    def __init__(self, textbox, cores_md, cores_tk):
        super().__init__()
        self.textbox = textbox
        self.cores_md = cores_md
        self.cores_tk = cores_tk
        self.tag_stack = []
        self.list_level = 0
        self.in_code_block = False
        self.code_block_content = []
        self.code_block_language = None

    def handle_starttag(self, tag, attrs):
        if tag in ('h1', 'h2', 'h3', 'h4'):
            self.tag_stack.append(tag)
        elif tag in ('strong', 'b'):
            self.tag_stack.append('bold')
        elif tag in ('em', 'i'):
            self.tag_stack.append('italic')
        elif tag == 'code':
            if not self.in_code_block:
                self.tag_stack.append('code')
            else:
                for nome, valor in attrs:
                    if nome == 'class' and valor.startswith('language-'):
                        self.code_block_language = valor.replace('language-', '')
        elif tag == 'pre':
            self.in_code_block = True
            self.code_block_content = []
            self.code_block_language = None
        elif tag == 'blockquote':
            self.tag_stack.append('quote')
        elif tag in ('ul', 'ol'):
            self.list_level += 1
        elif tag == 'li':
            indent = "  " * (self.list_level - 1)
            self.textbox.insert("end", f"{indent}• ", 'list')
        elif tag == 'hr':
            self.textbox.insert("end", "─" * 60 + "\n", 'list')

    def handle_endtag(self, tag):
        if tag in ('h1', 'h2', 'h3', 'h4'):
            if self.tag_stack and self.tag_stack[-1] in ('h1', 'h2', 'h3', 'h4'):
                self.tag_stack.pop()
            self.textbox.insert("end", "\n")
        elif tag in ('strong', 'b'):
            if self.tag_stack and self.tag_stack[-1] == 'bold':
                self.tag_stack.pop()
        elif tag in ('em', 'i'):
            if self.tag_stack and self.tag_stack[-1] == 'italic':
                self.tag_stack.pop()
        elif tag == 'code':
            if self.tag_stack and self.tag_stack[-1] == 'code':
                self.tag_stack.pop()
        elif tag == 'blockquote':
            if self.tag_stack and self.tag_stack[-1] == 'quote':
                self.tag_stack.pop()
        elif tag == 'pre':
            self.in_code_block = False
            codigo = ''.join(self.code_block_content)
            if codigo.strip():
                self._highlight(codigo, self.code_block_language)
            self.textbox.insert("end", "\n")
            self.code_block_content = []
            self.code_block_language = None
        elif tag in ('ul', 'ol'):
            self.list_level -= 1
        elif tag == 'li':
            self.textbox.insert("end", "\n")
        elif tag == 'p':
            self.textbox.insert("end", "\n")

    def _highlight(self, codigo, linguagem):
        """Tokeniza o bloco com Pygments e insere token a token."""
        try:
            if linguagem:
                try:
                    lexer = get_lexer_by_name(linguagem.lower(), stripall=True)
                except ClassNotFound:
                    lexer = TextLexer()
            else:
                lexer = TextLexer()

            fundo = self.cores_md['code_bg']
            for tipo, cor in self.cores_tk.items():
                self.textbox.tag_config(tipo, foreground=cor, background=fundo)

            for tipo, valor in lex(codigo, lexer):
                completo = str(tipo)
                curto = completo.split('.')[-1]
                if completo in self.cores_tk:
                    self.textbox.insert("end", valor, completo)
                elif curto in self.cores_tk:
                    self.textbox.insert("end", valor, curto)
                else:
                    self.textbox.insert("end", valor, 'code_block')
        except Exception:
            self.textbox.insert("end", codigo, 'code_block')

    def handle_data(self, data):
        if self.in_code_block:
            self.code_block_content.append(data)
        elif data:
            # Antes: `elif data.strip()`, que descartava os espacos entre spans
            # inline e colava as palavras vizinhas.
            if self.tag_stack:
                self.textbox.insert("end", data, tuple(self.tag_stack))
            else:
                self.textbox.insert("end", data)


def configurar_tags(textbox, cores):
    """Configura as tags de formatacao Markdown no textbox."""
    textbox.tag_config("h1", foreground=cores['h1'], spacing1=10, spacing3=5)
    textbox.tag_config("h2", foreground=cores['h2'], spacing1=8, spacing3=4)
    textbox.tag_config("h3", foreground=cores['h3'], spacing1=6, spacing3=3)
    textbox.tag_config("h4", foreground=cores['h4'], spacing1=4, spacing3=2)
    textbox.tag_config("bold", foreground=cores['bold'])
    textbox.tag_config("italic", foreground=cores['italic'])
    textbox.tag_config("code", background=cores['code_bg'], foreground=cores['code_fg'])
    textbox.tag_config("code_block", background=cores['code_bg'], foreground=cores['code_fg'])
    textbox.tag_config("quote", foreground=cores['quote'], lmargin1=20, lmargin2=20)
    textbox.tag_config("list", lmargin1=20, lmargin2=40)


def render_markdown(textbox, texto, cores_md, cores_tk):
    """Escreve o Markdown renderizado no fim do textbox.

    Nao limpa o widget: quem chama ja escreveu o cabecalho. (Na versao anterior
    o cabecalho era inserido em "1.0" depois da renderizacao, o que deslocava os
    indices das tags ja posicionadas.)
    """
    try:
        configurar_tags(textbox, cores_md)
        html = markdown.markdown(texto, extensions=['fenced_code'])
        HTMLToTkinterParser(textbox, cores_md, cores_tk).feed(html)
    except Exception as e:
        textbox.insert("end", f"[ERRO AO RENDERIZAR MARKDOWN: {e}]\n\n")
        textbox.insert("end", texto)
