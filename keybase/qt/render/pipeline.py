"""Markdown -> HTML pronto para o QTextBrowser.

Funcao pura: entra string, sai string. Nao importa Qt, entao roda em teste sem
display.

Na versao CustomTkinter este HTML era gerado e JOGADO FORA, para ser
reconstruido como tags de um tk.Text por um parser de 165 linhas. Aqui ele e o
produto final.
"""

import markdown

from ..theme import cores_markdown
from .estilo import folha_de_estilo
from .pos_html import AjustesFinais, AjustesParaQt

#: Extensoes habilitadas. Cada uma esta aqui por um motivo; ver RECUSADAS.
EXTENSOES = [
    'tables',                   # pedido explicito; o Qt desenha <table>
    'footnotes',                # [^1]
    'sane_lists',               # impede que um "1." no meio de um paragrafo vire lista
    'nl2br',                    # quebra digitada = quebra vista; e o que se espera
                                # de notas escritas a mao
    'toc',                      # poe id nos cabecalhos (ancoragem) e habilita [TOC]
    'pymdownx.superfences',     # substitui fenced_code: trata cerca aninhada e
                                # cerca dentro de lista, que o fenced_code quebra
    'pymdownx.highlight',
    'pymdownx.tilde',           # ~~riscado~~, inexistente no core
    'pymdownx.tasklist',        # - [ ] / - [x], inexistente no core
    'pymdownx.saneheaders',     # exige espaco depois do #, senao "#!/bin/bash" e
                                # "#config" viram H1 - acontece toda semana numa
                                # base de notas tecnicas
]

CONFIG_EXTENSOES = {
    'pymdownx.highlight': {'use_pygments': False},   # o realce e nosso, inline
    'pymdownx.tilde': {'subscript': False},          # senao ~/caminho ~ x vira subscrito
    'pymdownx.tasklist': {'clickable_checkbox': False},
    'toc': {'permalink': False},
    'footnotes': {'BACKLINK_TEXT': '&#8617;'},
}

# Extensoes RECUSADAS de proposito, com o motivo - nao reintroduzir sem pensar:
#
# attr_list  consome `{...}` no fim de um bloco e transforma em atributos. Uma
#            nota terminada em `{ "debug": true }` perderia esse trecho no
#            render. E a mesma classe do bug historico do CTRL_S: conteudo do
#            usuario comido em silencio.
# extra      bundle que arrasta attr_list e md_in_html junto. Listar uma a uma.
# smarty     curva aspas e vira -- em travessao, o que torna comando de shell
#            nao copiavel.
# def_list   dispara com qualquer linha seguida de ": algo", comum em fragmento
#            YAML ou ini.
# codehilite superada por pymdownx.highlight.


class RenderizadorMarkdown:
    """Converte Markdown em HTML para o Qt.

    A instancia de markdown.Markdown e reaproveitada com reset() a cada
    conversao. Isso importa por dois motivos: markdown.markdown() (a funcao)
    reconstroi o parser inteiro a cada chamada, caro num preview ao vivo; e sem
    reset() as extensoes footnotes e toc ACUMULAM estado entre conversoes, e as
    notas de rodape da nota anterior reaparecem na seguinte.
    """

    def __init__(self, tema='dark', fontes=None):
        self.tema = tema
        self.fontes = fontes or {}
        self.cores = cores_markdown(tema)
        self._md = self._construir()

    def _construir(self):
        md = markdown.Markdown(
            extensions=EXTENSOES,
            extension_configs=CONFIG_EXTENSOES,
            output_format='html',
        )
        md.treeprocessors.register(
            AjustesParaQt(md, self.tema, self.cores), 'ajustes_qt', 1
        )
        # prioridade 15: depois de raw_html (30) e amp_substitute (20), para ver
        # o HTML ja resolvido do htmlStash e nao ter o resultado reprocessado
        md.postprocessors.register(
            AjustesFinais(md, self.tema, self.cores), 'ajustes_qt_finais', 15
        )
        return md

    def html(self, texto):
        """Markdown -> HTML. Nunca levanta: degrada para texto pre-formatado."""
        try:
            self._md.reset()
            return self._md.convert(texto or '')
        except Exception as e:
            import html as _html
            return (f'<p style="color:{self.cores["h4"]}">'
                    f'[erro ao renderizar Markdown: {_html.escape(str(e))}]</p>'
                    f'<pre>{_html.escape(texto or "")}</pre>')

    def folha_de_estilo(self):
        return folha_de_estilo(self.tema, self.fontes)
