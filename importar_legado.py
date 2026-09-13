#!/usr/bin/env python3
"""Converte um data.json no formato antigo para a arvore do KeyBase 2.

Script avulso: o app nao o importa e nao depende dele. Existe so para quem
quiser aproveitar o conteudo cadastrado nas versoes 1.x.

Cada programa vira uma pasta na raiz. Atalhos, notas e snippets viram
sub-pastas com os itens dentro como notas em Markdown. Um snippet vira uma nota
cujo conteudo ja e um bloco de codigo cercado.

    python importar_legado.py data.json                   # previa, nao grava
    python importar_legado.py data.json --saida arvore.json
    python importar_legado.py data.json --achatado        # sem sub-pastas de tipo

Nunca sobrescreve um arquivo existente sem --forcar, e nunca toca no arquivo de
entrada.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from keybase import storage, tree
from keybase.model import nova_raiz


def _nome_unico(pai, nome, indice):
    """Garante nomes distintos entre irmaos, preservando o original quando da."""
    nome = (nome or "").strip() or f"item {indice}"
    nome = nome.replace("\n", " ").strip()
    if tree.nome_disponivel(pai, nome):
        return nome
    sufixo = 2
    while not tree.nome_disponivel(pai, f"{nome} ({sufixo})"):
        sufixo += 1
    return f"{nome} ({sufixo})"


def _nota_de_atalho(atalho):
    return (atalho.get("descricao") or "").strip() + "\n"


def _nota_de_nota(nota):
    return (nota.get("texto") or "").strip() + "\n"


def _nota_de_snippet(snippet):
    codigo = (snippet.get("codigo") or "").rstrip()
    linguagem = (snippet.get("linguagem") or "").strip()
    if linguagem == "markdown" or "```" in codigo:
        return codigo + "\n"
    return f"```{linguagem}\n{codigo}\n```\n"


SECOES = [
    ("atalhos", "Atalhos", "combinacao", _nota_de_atalho),
    ("notas", "Notas", "descricao", _nota_de_nota),
    ("snippets", "Snippets", "descricao", _nota_de_snippet),
]


def converter(legado, achatado=False):
    raiz = nova_raiz()
    total_pastas = total_notas = 0

    for i, programa in enumerate(legado.get("programas", []), start=1):
        pasta = tree.novo_folder(
            _nome_unico(raiz, programa.get("nome"), i),
            (programa.get("descricao") or "").strip(),
        )
        tree.adicionar(raiz, pasta)
        total_pastas += 1

        for chave, rotulo, campo_nome, monta_conteudo in SECOES:
            itens = programa.get(chave) or []
            if not itens:
                continue

            destino = pasta
            if not achatado:
                destino = tree.novo_folder(_nome_unico(pasta, rotulo, 1))
                tree.adicionar(pasta, destino)
                total_pastas += 1

            for j, item in enumerate(itens, start=1):
                if not isinstance(item, dict):
                    continue
                nota = tree.novo_file(
                    _nome_unico(destino, item.get(campo_nome), j),
                    monta_conteudo(item),
                )
                tree.adicionar(destino, nota)
                total_notas += 1

    return raiz, total_pastas, total_notas


def imprimir_arvore(no, prefixo="", ultimo=True):
    from keybase.model import Folder
    marcador = "└── " if ultimo else "├── "
    if prefixo or not isinstance(no, Folder) or no.nome != "KeyBase":
        sufixo = "/" if isinstance(no, Folder) else ""
        print(f"{prefixo}{marcador}{no.nome}{sufixo}")
        prefixo = prefixo + ("    " if ultimo else "│   ")
    if isinstance(no, Folder):
        filhos = tree.filhos_ordenados(no)
        for i, filho in enumerate(filhos):
            imprimir_arvore(filho, prefixo, i == len(filhos) - 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("entrada", help="data.json no formato antigo")
    parser.add_argument("--saida", help="arquivo a gravar (padrão: só mostra a prévia)")
    parser.add_argument("--achatado", action="store_true",
                        help="sem as sub-pastas Atalhos/Notas/Snippets")
    parser.add_argument("--forcar", action="store_true",
                        help="sobrescrever a saída se já existir")
    args = parser.parse_args()

    entrada = Path(args.entrada)
    if not entrada.exists():
        parser.error(f"arquivo não encontrado: {entrada}")

    try:
        legado = json.loads(entrada.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        parser.error(f"JSON inválido em {entrada}: {e}")

    if "programas" not in legado:
        parser.error(f"{entrada} não parece estar no formato antigo (sem 'programas')")

    raiz, pastas, notas = converter(legado, achatado=args.achatado)

    print(f"Lido:  {entrada}  ({len(legado['programas'])} programas)")
    print(f"Gerado: {pastas} pastas, {notas} notas\n")
    imprimir_arvore(raiz)

    if not args.saida:
        print("\nPrévia apenas. Use --saida ARQUIVO para gravar.")
        return 0

    saida = Path(args.saida)
    if saida.exists() and not args.forcar:
        print(f"\n{saida} já existe. Use --forcar para sobrescrever.", file=sys.stderr)
        return 1

    doc = storage.Documento(raiz)
    storage.salvar(doc, saida)
    print(f"\nGravado em {saida}")
    print("Para usar: feche o KeyBase e renomeie este arquivo para keybase_data.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
