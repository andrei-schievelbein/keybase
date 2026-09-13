"""Modelo de dados: a arvore de folders e files.

Dataclasses "burras" - sem logica de arvore, que vive em tree.py. Isso mantem
o modelo serializavel e testavel sem GUI.

Nota sobre heranca: todo campo de Node tem default, o que e obrigatorio para
que Folder e File possam acrescentar campos proprios sem TypeError.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

ID_RAIZ = "raiz"


def agora_iso():
    """Timestamp UTC em ISO-8601, com precisao de segundos."""
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def novo_id():
    return uuid.uuid4().hex


class EsquemaInvalidoError(Exception):
    """JSON valido, mas com forma que nao corresponde ao modelo."""


@dataclass
class Node:
    id: str = field(default_factory=novo_id)
    nome: str = ""
    criado_em: str = field(default_factory=agora_iso)
    atualizado_em: str = field(default_factory=agora_iso)

    def touch(self):
        self.atualizado_em = agora_iso()


@dataclass
class Folder(Node):
    descricao: str = ""
    filhos: list = field(default_factory=list)

    def to_dict(self):
        return {
            "id": self.id,
            "tipo": "folder",
            "nome": self.nome,
            "descricao": self.descricao,
            "criado_em": self.criado_em,
            "atualizado_em": self.atualizado_em,
            "filhos": [f.to_dict() for f in self.filhos],
        }


@dataclass
class File(Node):
    conteudo: str = ""

    def to_dict(self):
        return {
            "id": self.id,
            "tipo": "file",
            "nome": self.nome,
            "conteudo": self.conteudo,
            "criado_em": self.criado_em,
            "atualizado_em": self.atualizado_em,
        }


def _texto(bruto, chave, contexto, obrigatorio=False):
    valor = bruto.get(chave, "")
    if valor is None:
        valor = ""
    if not isinstance(valor, str):
        raise EsquemaInvalidoError(
            f"{contexto}: campo '{chave}' deveria ser texto, veio {type(valor).__name__}"
        )
    if obrigatorio and not valor:
        raise EsquemaInvalidoError(f"{contexto}: campo '{chave}' vazio ou ausente")
    return valor


def node_from_dict(bruto, reparos=None):
    """Reconstroi um no a partir do dict lido do JSON.

    O unico reparo tolerado e o no sem 'id' (arquivo editado a mao): gera um id
    e registra em `reparos`. Qualquer outro desvio e erro - carregar nunca
    inventa dados.
    """
    if not isinstance(bruto, dict):
        raise EsquemaInvalidoError(f"no deveria ser um objeto, veio {type(bruto).__name__}")

    tipo = bruto.get("tipo")
    if tipo not in ("folder", "file"):
        raise EsquemaInvalidoError(f"tipo desconhecido: {tipo!r}")

    nome = _texto(bruto, "nome", f"no {tipo}")
    contexto = f"{tipo} {nome!r}"

    id_ = bruto.get("id")
    if not isinstance(id_, str) or not id_:
        id_ = novo_id()
        if reparos is not None:
            reparos.append(f"{contexto}: sem id, um novo foi gerado")

    criado = _texto(bruto, "criado_em", contexto) or agora_iso()
    atualizado = _texto(bruto, "atualizado_em", contexto) or criado

    if tipo == "file":
        return File(
            id=id_,
            nome=nome,
            criado_em=criado,
            atualizado_em=atualizado,
            conteudo=_texto(bruto, "conteudo", contexto),
        )

    filhos_brutos = bruto.get("filhos", [])
    if not isinstance(filhos_brutos, list):
        raise EsquemaInvalidoError(f"{contexto}: 'filhos' deveria ser uma lista")

    return Folder(
        id=id_,
        nome=nome,
        criado_em=criado,
        atualizado_em=atualizado,
        descricao=_texto(bruto, "descricao", contexto),
        filhos=[node_from_dict(f, reparos) for f in filhos_brutos],
    )


def nova_raiz():
    """Folder raiz de uma base vazia. A raiz e um Folder real, nao lista solta."""
    return Folder(id=ID_RAIZ, nome="KeyBase")
