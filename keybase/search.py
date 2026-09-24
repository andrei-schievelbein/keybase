"""Busca recursiva na arvore, por nome, descricao e conteudo markdown.

Cada Resultado carrega seus proprios ancestrais, coletados durante o DFS. E
isso que permite "pular" para um hit em qualquer profundidade sem nenhuma
busca reversa - e que mata, por construcao, o bug de indexacao da versao
anterior (a lista exibida vinha dos resultados, mas o numero digitado indexava
a lista global).
"""

from dataclasses import dataclass

from .model import File, Folder, Node
from .tree import normalizar, percorrer

TERMO_MINIMO = 2
LIMITE_PADRAO = 50
CONTEXTO_TRECHO = 40
MAX_TRECHO = 90


@dataclass(frozen=True)
class Resultado:
    no: Node
    ancestrais: tuple
    campo: str          # "nome" | "descricao" | "conteudo"
    score: int
    trecho: str = ""

    @property
    def caminho(self):
        nomes = [a.nome for a in self.ancestrais[1:]]  # pula a raiz
        return " / ".join(nomes) if nomes else "(raiz)"

    @property
    def e_pasta(self):
        return isinstance(self.no, Folder)

    @property
    def rotulo_tipo(self):
        return "pasta" if self.e_pasta else "nota"


class TermoCurtoError(ValueError):
    """Termo com menos de TERMO_MINIMO caracteres."""


def trecho(conteudo, pos, tam, contexto=CONTEXTO_TRECHO):
    """Recorte do conteudo ao redor da ocorrencia, em texto plano.

    Colapsa quebras de linha para a lista de resultados nao explodir em altura.
    """
    inicio = max(0, pos - contexto)
    fim = min(len(conteudo), pos + tam + contexto)
    recorte = ' '.join(conteudo[inicio:fim].split())
    if inicio > 0:
        recorte = '...' + recorte
    if fim < len(conteudo):
        recorte = recorte + '...'
    if len(recorte) > MAX_TRECHO:
        recorte = recorte[:MAX_TRECHO - 3] + '...'
    return recorte


def distancia(a, b):
    """Levenshtein com transposicao (Damerau restrito): 'cotnrol' ~ 'control'."""
    anterior2 = None
    anterior = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        atual = [i] + [0] * len(b)
        for j, cb in enumerate(b, start=1):
            custo = 0 if ca == cb else 1
            atual[j] = min(anterior[j] + 1, atual[j - 1] + 1, anterior[j - 1] + custo)
            if (i > 1 and j > 1 and ca == b[j - 2] and a[i - 2] == cb
                    and anterior2 is not None):
                atual[j] = min(atual[j], anterior2[j - 2] + 1)
        anterior2, anterior = anterior, atual
    return anterior[-1]


def _tolerancia(termo):
    """Erros de digitacao aceitos: nenhum em termo curto, onde tudo casaria."""
    if len(termo) < 4:
        return 0
    return 1 if len(termo) <= 6 else 2


def parecido(termo_norm, nome_norm):
    """O nome casa com o termo por erro de digitacao, palavra a palavra."""
    limite = _tolerancia(termo_norm)
    if not limite:
        return False
    palavras = nome_norm.split() + [nome_norm]
    for palavra in palavras:
        # compara tambem com o comeco da palavra: 'vscdoe' ~ 'vscode-insiders'
        for alvo in (palavra, palavra[:len(termo_norm)]):
            if abs(len(alvo) - len(termo_norm)) <= limite and \
                    distancia(termo_norm, alvo) <= limite:
                return True
    return False


def _avaliar(no, termo_norm):
    """Melhor pontuacao do no e o campo que casou. Um hit por no."""
    nome_norm = normalizar(no.nome)

    if nome_norm == termo_norm:
        return 100, "nome", ""
    if nome_norm.startswith(termo_norm):
        return 80, "nome", ""
    if termo_norm in nome_norm:
        return 60, "nome", ""

    if isinstance(no, Folder):
        if termo_norm in normalizar(no.descricao):
            return 40, "descricao", ""
        if parecido(termo_norm, nome_norm):
            return 10, "aproximado", ""
        return 0, "", ""

    if no.conteudo is None:
        # nota cifrada com o cofre trancado: so o nome conta
        return (10, "aproximado", "") if parecido(termo_norm, nome_norm) else (0, "", "")

    conteudo_norm = normalizar(no.conteudo)
    if termo_norm in conteudo_norm:
        ocorrencias = conteudo_norm.count(termo_norm)
        pos = conteudo_norm.find(termo_norm)
        return (20 + min(ocorrencias, 5), "conteudo",
                trecho(no.conteudo, pos, len(termo_norm)))

    # abaixo de qualquer acerto exato: erro de digitacao no nome
    if parecido(termo_norm, nome_norm):
        return 10, "aproximado", ""
    return 0, "", ""


def buscar(escopo, termo, limite=LIMITE_PADRAO):
    """Resultados ordenados por relevancia. Levanta TermoCurtoError se curto."""
    termo = (termo or "").strip()
    if len(termo) < TERMO_MINIMO:
        raise TermoCurtoError(
            f"digite pelo menos {TERMO_MINIMO} caracteres para buscar"
        )

    termo_norm = normalizar(termo)
    achados = []

    for no, ancestrais in percorrer(escopo):
        score, campo, recorte = _avaliar(no, termo_norm)
        if score:
            achados.append(Resultado(no, ancestrais, campo, score, recorte))

    # score desc; depois menor profundidade; depois caminho alfabetico
    achados.sort(key=lambda r: (-r.score, len(r.ancestrais), normalizar(r.caminho),
                                normalizar(r.no.nome)))
    return achados[:limite], len(achados)


def filtrar(folder, termo):
    """Filtro raso da pasta atual - o comando /termo, que nao sai do lugar."""
    termo_norm = normalizar(termo or "")
    if not termo_norm:
        return None
    from .tree import filhos_ordenados
    return [n for n in filhos_ordenados(folder) if termo_norm in normalizar(n.nome)]
