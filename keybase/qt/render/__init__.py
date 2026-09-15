"""Conversao de Markdown para o HTML que o QTextBrowser consome.

Nenhum modulo deste pacote importa Qt: e tudo string, testavel sem display.
"""

from .estilo import estilo_pygments, folha_de_estilo
from .pipeline import EXTENSOES, RenderizadorMarkdown

__all__ = ['RenderizadorMarkdown', 'folha_de_estilo', 'estilo_pygments', 'EXTENSOES']
