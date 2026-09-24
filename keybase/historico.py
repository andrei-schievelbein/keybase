"""Versoes antigas de uma nota, lidas do .bak e dos snapshots. Sem Qt.

Nenhum formato novo: os backups que o storage ja grava SAO o historico. Aqui
so se procura a nota pelo id em cada um deles.

Itens cifrados: a chave das notas (DEK) nunca muda - trocar a senha so
reenvelopa a DEK -, entao o cofre atual, destravado, abre as versoes antigas
cifradas, inclusive dentro de pastas cifradas. Sem o cofre, elas ficam de fora.
"""

import json
from dataclasses import dataclass

from . import cripto, storage


@dataclass(frozen=True)
class Versao:
    rotulo: str          # "Backup anterior (24/09/2026 14:30)", "Snapshot de 2026-09-19"
    atualizado_em: str   # da nota, naquela copia
    conteudo: str

    @property
    def n_linhas(self):
        return len(self.conteudo.splitlines())


def _achar(no, node_id, cofre):
    """O dict da nota dentro de um JSON bruto, abrindo pastas cifradas no caminho."""
    if not isinstance(no, dict):
        return None
    if no.get("id") == node_id and no.get("tipo") == "file":
        return no
    filhos = no.get("filhos")
    if no.get("cifrada"):
        if cofre is None or not cofre.destravado:
            return None
        try:
            filhos = json.loads(cofre.decifrar(no.get("filhos_cifrados"), no["id"]))["filhos"]
        except (cripto.CriptoError, ValueError, KeyError, TypeError):
            return None
    for filho in filhos or ():
        achado = _achar(filho, node_id, cofre)
        if achado is not None:
            return achado
    return None


def _texto(nota, cofre):
    if nota.get("cifrado"):
        if cofre is None or not cofre.destravado:
            return None
        try:
            return cofre.decifrar(nota.get("conteudo_cifrado"), nota["id"])
        except (cripto.CriptoError, KeyError, TypeError):
            return None
    conteudo = nota.get("conteudo")
    return conteudo if isinstance(conteudo, str) else None


def versoes(caminho_dados, node_id, cofre=None, atual=None):
    """Versoes distintas da nota, da mais nova para a mais antiga.

    Pula as iguais a `atual` (o texto de agora), as repetidas (dez snapshots
    com o mesmo texto sao uma versao so) e as vazias: toda nota nasce vazia
    antes do primeiro Ctrl+S, e restaurar o nada nao serve a ninguem.
    """
    vistas = {atual} if atual is not None else set()
    achadas = []
    for rotulo, arquivo in storage.backups_disponiveis(caminho_dados):
        bruto = storage.ler_backup(arquivo)
        if bruto is None:
            continue
        nota = _achar(bruto["raiz"], node_id, cofre)
        if nota is None:
            continue
        texto = _texto(nota, cofre)
        if texto is None or not texto.strip() or texto in vistas:
            continue
        vistas.add(texto)
        achadas.append(Versao(rotulo, nota.get("atualizado_em", ""), texto))
    return achadas
