"""Tema da aplicacao: estilo, paleta e folha global.

Tres camadas, porque nenhuma sozinha cobre tudo:

1. Fusion - sem ele o estilo nativo do macOS ignora parte da paleta e desenha
   campo de texto e barra de rolagem com fundo claro em cima do tema escuro.
   Tambem deixa a aparencia igual nas tres plataformas, que e o que um
   emulador de terminal quer.
2. QPalette - alcanca o que o QSS nao alcanca: setas e trilho da barra de
   rolagem, menu de contexto do texto selecionado, tooltip, candidatos de IME.
3. QSS - o cromo dos widgets nomeados, aplicado na janela.
"""

from PySide6.QtGui import QColor, QPalette

from .theme import cores_interface


def paleta(tema):
    cores = cores_interface(tema)
    p = QPalette()
    fundo = QColor(cores['fundo'])
    texto = QColor(cores['texto'])

    p.setColor(QPalette.ColorRole.Window, fundo)
    p.setColor(QPalette.ColorRole.WindowText, texto)
    p.setColor(QPalette.ColorRole.Base, QColor(cores['entrada_bg']))
    p.setColor(QPalette.ColorRole.AlternateBase, fundo)
    p.setColor(QPalette.ColorRole.Text, texto)
    p.setColor(QPalette.ColorRole.Button, fundo)
    p.setColor(QPalette.ColorRole.ButtonText, texto)
    p.setColor(QPalette.ColorRole.Highlight, QColor(cores['selecao']))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor(cores['selecao_texto']))
    p.setColor(QPalette.ColorRole.ToolTipBase, QColor(cores['help_bg']))
    p.setColor(QPalette.ColorRole.ToolTipText, QColor(cores['help_fg']))
    return p


def aplicar_tema(qapp, tema):
    qapp.setStyle('Fusion')
    qapp.setPalette(paleta(tema))
