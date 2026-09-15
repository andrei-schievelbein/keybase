"""Atalhos de teclado, com o tratamento do macOS num lugar so.

No macOS o Qt troca Ctrl e Meta por padrao: `QKeySequence("Ctrl+1")` vira
Cmd+1. Quem aperta o Ctrl FISICO nao dispara nada - foi exatamente o que
aconteceu com Ctrl+1/2/3 e Ctrl+E.

A solucao aqui e registrar as DUAS variantes no macOS (Cmd, que e a convencao
nativa, e o Ctrl fisico), para que qualquer uma funcione. Nas outras
plataformas so a variante Ctrl e registrada - la Meta e a tecla Windows/Super,
e registra-la criaria atalho onde ninguem espera.
"""

import sys

from PySide6.QtGui import QKeySequence

SALVAR = 'Ctrl+S'
CANCELAR = 'Esc'
MODO_EDITAR = 'Ctrl+1'
MODO_PREVIEW = 'Ctrl+2'
MODO_DIVIDIDO = 'Ctrl+3'
MODO_CICLAR = 'Ctrl+E'

NO_MACOS = sys.platform == 'darwin'


def variantes(sequencia):
    """Todas as combinacoes que devem disparar esta acao."""
    base = QKeySequence(sequencia)
    saida = [base]

    if NO_MACOS:
        portavel = base.toString(QKeySequence.SequenceFormat.PortableText)
        if portavel.startswith('Ctrl+'):
            # o Ctrl fisico do teclado, que o Qt chama de Meta no macOS
            saida.append(QKeySequence('Meta+' + portavel[len('Ctrl+'):]))

    return saida


def rotulo(sequencia):
    """Como mostrar o atalho ao usuario, na convencao da plataforma.

    No macOS devolve os simbolos (⌘S), que e o que o usuario reconhece.
    """
    return QKeySequence(sequencia).toString(QKeySequence.SequenceFormat.NativeText)
