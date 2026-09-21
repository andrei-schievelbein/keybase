"""Operacoes puras sobre a arvore. Sem I/O, sem GUI.

A ordem dos filhos e DERIVADA (folders antes de files, alfabetico dentro de
cada grupo), nunca armazenada. Por isso nao existe comando de reordenar.

INVARIANTE: filhos_ordenados() e a unica fonte de numeracao das telas. Nenhum
codigo pode indexar folder.filhos diretamente com um numero digitado pelo
usuario - a ordem exibida difere da ordem em filhos, e foi exatamente esse
descasamento que causou o bug de indexacao da busca na versao anterior.
"""

import unicodedata

from .model import File, Folder, Node, novo_id


class CicloError(Exception):
    """Tentativa de mover um folder para dentro de si mesmo."""


class NomeDuplicadoError(Exception):
    """Ja existe um irmao com esse nome."""


def normalizar(texto):
    """Minusculas, sem acentos - para ordenacao e busca estaveis.

    Usa NFKD em vez de locale, que e inconsistente no Windows.
    """
    decomposto = unicodedata.normalize('NFKD', texto or "")
    sem_acento = ''.join(c for c in decomposto if not unicodedata.combining(c))
    return sem_acento.casefold()


# --- criacao ---------------------------------------------------------------

def novo_folder(nome, descricao=""):
    return Folder(nome=nome, descricao=descricao)


def novo_file(nome, conteudo=""):
    return File(nome=nome, conteudo=conteudo)


# --- mutacao ---------------------------------------------------------------

def adicionar(pai, no):
    pai.filhos.append(no)
    pai.touch()


def remover(pai, no):
    pai.filhos.remove(no)
    pai.touch()


def renomear(no, nome):
    no.nome = nome
    no.touch()


def definir_descricao(folder, texto):
    folder.descricao = texto
    folder.touch()


def definir_conteudo(file, markdown):
    file.conteudo = markdown
    file.touch()


def mover(no, origem, destino):
    """Reparenta um no. Disponivel na API, fora da UI no v1."""
    if no is destino or _contem(no, destino):
        raise CicloError(f"nao da para mover {no.nome!r} para dentro de si mesmo")
    origem.filhos.remove(no)
    destino.filhos.append(no)
    origem.touch()
    destino.touch()


def _contem(possivel_ancestral, no):
    if not isinstance(possivel_ancestral, Folder):
        return False
    for filho in possivel_ancestral.filhos:
        if filho is no or _contem(filho, no):
            return True
    return False


# --- consulta --------------------------------------------------------------

def chave_ordenacao(no):
    return (0 if isinstance(no, Folder) else 1, normalizar(no.nome))


def filhos_ordenados(folder):
    """Folders primeiro, depois files; cada grupo em ordem alfabetica.

    Unica fonte de numeracao das telas (ver docstring do modulo).
    """
    return sorted(folder.filhos, key=chave_ordenacao)


def construir_indice(raiz):
    """Mapa id -> (no, pai). Reconstruido inteiro a cada mutacao.

    Com algumas centenas de nos isso custa microssegundos e elimina toda uma
    classe de bug de indice desatualizado. Nao fazer manutencao incremental.
    """
    indice = {}

    def visitar(no, pai):
        indice[no.id] = (no, pai)
        if isinstance(no, Folder):
            for filho in no.filhos:
                visitar(filho, no)

    visitar(raiz, None)
    return indice


def caminho(indice, no):
    """Cadeia da raiz ate o no, inclusive."""
    cadeia = []
    atual = no
    while atual is not None:
        cadeia.append(atual)
        entrada = indice.get(atual.id)
        atual = entrada[1] if entrada else None
    cadeia.reverse()
    return cadeia


def breadcrumb(cadeia, sep=" / "):
    """Texto do caminho, pulando a raiz."""
    return sep.join(no.nome for no in cadeia[1:])


def contar_itens(folder):
    """Filhos diretos - o '[N]' da listagem."""
    return len(folder.filhos)


def contar_notas(folder):
    """(diretas, na subarvore inteira) - o '[a]:[b]' da listagem.

    So notas: sub-pasta nao entra em nenhuma das duas metades. A segunda reusa
    contar_recursivo, que ja fazia essa caminhada para o resumo de delecao.
    """
    diretas = sum(1 for filho in folder.filhos if isinstance(filho, File))
    return diretas, contar_recursivo(folder)[1]


def contar_recursivo(folder):
    """(n_folders, n_files) em toda a subarvore, sem contar o proprio folder."""
    pastas = notas = 0
    for filho in folder.filhos:
        if isinstance(filho, Folder):
            pastas += 1
            sub_p, sub_n = contar_recursivo(filho)
            pastas += sub_p
            notas += sub_n
        else:
            notas += 1
    return pastas, notas


def percorrer(raiz):
    """DFS carregando a pilha de ancestrais de cada no.

    Rende (no, ancestrais) onde ancestrais vai da raiz ate o pai, inclusive.
    A raiz em si nao e rendida.
    """
    def visitar(folder, ancestrais):
        for filho in filhos_ordenados(folder):
            yield filho, ancestrais
            if isinstance(filho, Folder):
                yield from visitar(filho, ancestrais + (filho,))

    yield from visitar(raiz, (raiz,))


def nome_disponivel(pai, nome, ignorar=None):
    """False se ja existe um irmao com esse nome (ignorando caixa e acento)."""
    alvo = normalizar(nome)
    for filho in pai.filhos:
        if filho is ignorar:
            continue
        if normalizar(filho.nome) == alvo:
            return False
    return True


def resumo_delecao(no):
    """Frase descrevendo o que sera apagado, para a confirmacao."""
    if isinstance(no, File):
        return f"a nota {no.nome!r}"
    pastas, notas = contar_recursivo(no)
    if pastas == 0 and notas == 0:
        return f"a pasta vazia {no.nome!r}"
    partes = []
    if pastas:
        partes.append(f"{pastas} pasta{'s' if pastas != 1 else ''}")
    if notas:
        partes.append(f"{notas} nota{'s' if notas != 1 else ''}")
    return f"a pasta {no.nome!r} e TUDO dentro ({', '.join(partes)})"


def precisa_confirmacao_forte(no):
    """Folder nao vazio exige digitar DELETAR; o resto aceita s/n."""
    return isinstance(no, Folder) and bool(no.filhos)


def preview_conteudo(file, limite=70):
    """Primeira linha util do markdown, para listagens."""
    for linha in file.conteudo.splitlines():
        limpa = linha.strip().lstrip('#').strip()
        if limpa:
            return limpa[:limite] + ('...' if len(limpa) > limite else '')
    return ""
