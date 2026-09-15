"""Escolha da fonte monoespacada.

Todo o alinhamento do terminal (barras de '=', contadores alinhados a direita,
truncamento com reticencias) e calculado contando caracteres, o que so funciona
com fonte monoespacada de verdade.

Pedir uma familia inexistente NAO levanta erro nem no Tk nem no Qt: o
framework substitui em silencio por uma proporcional. Foi assim que o
alinhamento quebrou no macOS, onde 'Consolas' nao existe. Aqui a substituicao e
detectada comparando o que foi pedido com o que o Qt realmente resolveu.
"""

from PySide6.QtGui import QFont, QFontDatabase, QFontInfo, QFontMetricsF

#: Usadas quando a familia configurada nao existe nesta maquina.
MONOESPACADAS = ('Consolas', 'Menlo', 'DejaVu Sans Mono', 'Courier New',
                 'Monaco', 'Liberation Mono', 'Courier')

#: Caracteres que precisam ter a mesma largura para o alinhamento fechar.
AMOSTRA = ('0', 'W', 'i', '=', '~')

#: Usado no truncamento; se vier de uma fonte substituta, a linha desalinha.
RETICENCIAS = '…'


def criar_fonte(familia, tamanho):
    fonte = QFont(familia, tamanho)
    fonte.setStyleHint(QFont.StyleHint.Monospace)  # guia o fallback de glifo
    fonte.setFixedPitch(True)
    fonte.setKerning(False)
    return fonte


def e_monoespacada(familia, tamanho):
    """True se o Qt resolver esta familia como monoespacada de fato.

    Tres verificacoes independentes, e as tres importam:
    1. a familia resolvida e a pedida - pega a substituicao silenciosa
    2. os caracteres da amostra tem a mesma largura - e disso que o layout
       depende; e a autoridade
    3. fixedPitch() - le uma flag declarada na fonte, nem sempre confiavel,
       serve so como confirmacao
    """
    fonte = criar_fonte(familia, tamanho)
    info = QFontInfo(fonte)
    if info.family().lower() != familia.lower():
        return False
    metrica = QFontMetricsF(fonte)
    larguras = {metrica.horizontalAdvance(c) for c in AMOSTRA}
    return len(larguras) == 1 and info.fixedPitch()


def escolher_familia(fontes, tamanho):
    """Primeira familia monoespacada que exista e seja resolvida como tal.

    Diferente do Tk, o Qt sempre tem uma resposta garantida no fim
    (systemFont(FixedFont)), entao esta funcao nunca devolve uma familia
    proporcional.
    """
    disponiveis = {f.lower() for f in QFontDatabase.families()}

    preferidas = [fontes.get('family'), fontes.get('fallback')]
    preferidas += [f for f in MONOESPACADAS if f not in preferidas]

    for familia in preferidas:
        if familia and familia.lower() in disponiveis and e_monoespacada(familia, tamanho):
            return familia

    return QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont).family()


def largura_caractere(fonte):
    """Avanco de um caractere, em pixels (float).

    horizontalAdvance('0') e nao averageCharWidth(): o segundo e um inteiro
    derivado de uma media declarada na fonte, que numa proporcional devolve um
    numero plausivel e errado. QFontMetricsF (float) porque em HiDPI o avanco
    raramente e inteiro, e arredondar cedo acumula erro ao longo de 80 colunas.
    """
    return QFontMetricsF(fonte).horizontalAdvance('0')


def tem_reticencias(fonte):
    """False se o glifo de reticencias vier de uma fonte substituta."""
    from PySide6.QtGui import QFontMetrics
    return QFontMetrics(fonte).inFont(RETICENCIAS)
