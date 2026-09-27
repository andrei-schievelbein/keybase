"""Selecao de varios itens por numero: '3', '1,2,5', '1-4', '1-3, 7'.

Sem Qt: e so o parsing, compartilhado pela pergunta "qual item?" e pelos
comandos com lista na barra (C1,2,5).
"""

import re

#: texto que tem cara de lista de numeros - o resto nao e selecao
PADRAO_LISTA = re.compile(r'^[\d\s,\-]+$')


class SelecaoInvalida(ValueError):
    """A mensagem e para o usuario."""


def interpretar(texto, total):
    """Indices (a partir de 0) escolhidos, na ordem da lista e sem repeticao."""
    texto = (texto or "").strip()
    if not texto or not PADRAO_LISTA.match(texto):
        raise SelecaoInvalida(_dica(total))

    escolhidos = set()
    for parte in texto.split(','):
        parte = parte.strip()
        if not parte:
            continue
        if '-' in parte:
            inicio, _, fim = (p.strip() for p in parte.partition('-'))
            if not (inicio.isdigit() and fim.isdigit()):
                raise SelecaoInvalida(_dica(total))
            inicio, fim = int(inicio), int(fim)
            if inicio > fim:
                raise SelecaoInvalida(f"Intervalo invertido: {parte}. Use {fim}-{inicio}.")
            numeros = range(inicio, fim + 1)
        elif parte.isdigit():
            numeros = [int(parte)]
        else:
            raise SelecaoInvalida(_dica(total))
        for n in numeros:
            if not 1 <= n <= total:
                raise SelecaoInvalida(f"Não há item {n} na lista. {_dica(total)}")
            escolhidos.add(n - 1)

    if not escolhidos:
        raise SelecaoInvalida(_dica(total))
    return sorted(escolhidos)


def _dica(total):
    return (f"Digite o número do item, de 1 a {total}; vários com vírgula (1,2) "
            f"ou intervalo (1-{total}). ESC cancela.")


def descricao_lote(verbo, nos):
    """O que o U desfaz: "copiar 'Nota'" ou "copiar 3 itens"."""
    if len(nos) == 1:
        return f"{verbo} {nos[0].nome!r}"
    return f"{verbo} {len(nos)} itens"
