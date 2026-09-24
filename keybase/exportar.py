"""Exportar uma pasta (ou a base inteira) para arquivos .md comuns. Sem Qt.

A arvore vira pastas de verdade e cada nota vira Nome.md - legivel em
qualquer editor, e a saida para quem quiser migrar. Nada aqui grava no
arquivo de dados: exportar so le a arvore.

Itens cifrados: ou ficam de fora (incluir_cifrados=False), ou saem EM CLARO
com o cofre aberto. Nunca saem pela metade - nota cifrada trancada e pasta
cifrada trancada sao puladas e contadas.
"""

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .model import File, Folder
from .tree import filhos_ordenados

_PROIBIDOS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVADOS_WINDOWS = {'CON', 'PRN', 'AUX', 'NUL',
                       *(f'COM{i}' for i in range(1, 10)),
                       *(f'LPT{i}' for i in range(1, 10))}


@dataclass
class Resultado:
    pasta: Path
    notas: int = 0
    pastas: int = 0
    pulados: list = field(default_factory=list)   # nomes dos itens cifrados pulados


def nome_de_arquivo(nome):
    """Nome valido em Windows, macOS e Linux: '/' e cia viram '_'."""
    limpo = _PROIBIDOS.sub('_', nome).strip().rstrip('. ')
    if not limpo:
        limpo = '_'
    if limpo.split('.')[0].upper() in _RESERVADOS_WINDOWS:
        limpo = '_' + limpo
    return limpo[:120]


def _livre(pasta, base, sufixo=''):
    """'Nome.md', 'Nome (2).md'... - dois itens que sanitizam igual nao colidem."""
    candidato = pasta / f'{base}{sufixo}'
    n = 2
    while candidato.exists():
        candidato = pasta / f'{base} ({n}){sufixo}'
        n += 1
    return candidato


def pasta_de_saida(onde, nome_base='KeyBase-export'):
    """onde/KeyBase-export-AAAA-MM-DD, ou com (2), (3)... se ja existir."""
    return _livre(Path(onde), f'{nome_base}-{date.today().isoformat()}')


def exportar(no, destino, incluir_cifrados=False):
    """Exporta `no` (Folder ou File) para dentro de `destino`, que e criado.

    Com incluir_cifrados=True, quem chama garantiu o cofre aberto: o texto
    claro esta na memoria (nota.conteudo, pasta.filhos).
    """
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=False)
    resultado = Resultado(destino)
    if isinstance(no, File):
        _exportar_nota(no, destino, incluir_cifrados, resultado)
    else:
        _exportar_filhos(no, destino, incluir_cifrados, resultado,
                         protegida=no.cifrada)
    return resultado


def _exportar_filhos(pasta, destino, incluir, resultado, protegida):
    if pasta.descricao:
        (destino / '_descricao.md').write_text(pasta.descricao + '\n', encoding='utf-8')
    for filho in filhos_ordenados(pasta):
        if isinstance(filho, Folder):
            _exportar_pasta(filho, destino, incluir, resultado, protegida)
        else:
            _exportar_nota(filho, destino, incluir, resultado, protegida)


def _exportar_pasta(pasta, destino, incluir, resultado, protegida=False):
    protegida = protegida or pasta.cifrada
    if (protegida and not incluir) or pasta.trancada:
        resultado.pulados.append(pasta.nome + '/')
        return
    alvo = _livre(destino, nome_de_arquivo(pasta.nome))
    alvo.mkdir()
    resultado.pastas += 1
    _exportar_filhos(pasta, alvo, incluir, resultado, protegida)


def _exportar_nota(nota, destino, incluir, resultado, protegida=False):
    sensivel = nota.cifrado or protegida
    if (sensivel and not incluir) or nota.conteudo is None:
        resultado.pulados.append(nota.nome)
        return
    alvo = _livre(destino, nome_de_arquivo(nota.nome), '.md')
    alvo.write_text(nota.conteudo, encoding='utf-8')
    resultado.notas += 1
