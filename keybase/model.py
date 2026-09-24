"""Modelo de dados: a arvore de folders e files.

Dataclasses "burras" - sem logica de arvore, que vive em tree.py. Isso mantem
o modelo serializavel e testavel sem GUI.

Nota sobre heranca: todo campo de Node tem default, o que e obrigatorio para
que Folder e File possam acrescentar campos proprios sem TypeError.
"""

import json
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


class PastaNaoSeladaError(Exception):
    """Pasta cifrada aberta mudou e ninguem recifrou antes de serializar.

    Rede de seguranca: gravar o blob antigo perderia as mudancas em silencio.
    Quem salva deve chamar cripto.selar_pastas antes.
    """


def payload_pasta(descricao, filhos):
    """O texto que vai cifrado numa pasta cifrada: descricao e filhos (dicts).

    Um formato so, usado pelo modelo e pelo saneamento de backups, para que
    um backup saneado abra do mesmo jeito que o arquivo atual.
    """
    return json.dumps({"descricao": descricao, "filhos": filhos},
                      ensure_ascii=False, sort_keys=True)


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
    #: notas criadas aqui ja nascem cifradas. Escolhido ao criar a pasta.
    nasce_cifrada: bool = False
    #: pasta inteira cifrada: descricao e filhos vivem em `blob`. Trancada,
    #: `filhos` e None (nao []): quem percorrer sem checar falha alto, em vez
    #: de tratar a pasta como vazia e gravar o vazio por cima.
    cifrada: bool = False
    blob: dict = None
    #: payload do ultimo selamento - compara para so recifrar quando mudou
    selado: str = field(default=None, repr=False, compare=False)

    @property
    def trancada(self):
        return self.filhos is None

    def payload(self):
        return payload_pasta(self.descricao, [f.to_dict() for f in self.filhos])

    def to_dict(self):
        d = {
            "id": self.id,
            "tipo": "folder",
            "nome": self.nome,
        }
        if self.cifrada:
            if not self.trancada and self.payload() != self.selado:
                raise PastaNaoSeladaError(
                    f"pasta cifrada {self.nome!r} mudou e nao foi recifrada")
            d["cifrada"] = True
            d["filhos_cifrados"] = dict(self.blob)
            d["criado_em"] = self.criado_em
            d["atualizado_em"] = self.atualizado_em
            return d
        d["descricao"] = self.descricao
        d["criado_em"] = self.criado_em
        d["atualizado_em"] = self.atualizado_em
        if self.nasce_cifrada:  # so quando true: o arquivo comum nao muda
            d["nasce_cifrada"] = True
        d["filhos"] = [f.to_dict() for f in self.filhos]
        return d


@dataclass
class File(Node):
    #: texto claro. None numa nota cifrada com o cofre trancado.
    conteudo: str = ""
    cifrado: bool = False
    #: {"nonce", "ct"} - a verdade em disco de uma nota cifrada
    blob: dict = None

    def to_dict(self):
        d = {
            "id": self.id,
            "tipo": "file",
            "nome": self.nome,
        }
        # Nota cifrada NUNCA serializa o texto claro, nem com o cofre aberto.
        if self.cifrado:
            d["cifrado"] = True
            d["conteudo_cifrado"] = dict(self.blob)
        else:
            d["conteudo"] = self.conteudo
        d["criado_em"] = self.criado_em
        d["atualizado_em"] = self.atualizado_em
        return d


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


def _bool(bruto, chave, contexto):
    valor = bruto.get(chave, False)
    if not isinstance(valor, bool):
        raise EsquemaInvalidoError(
            f"{contexto}: campo '{chave}' deveria ser booleano, veio {type(valor).__name__}"
        )
    return valor


def _blob_valido(blob):
    return (isinstance(blob, dict)
            and isinstance(blob.get("nonce"), str)
            and isinstance(blob.get("ct"), str))


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
        cifrado = _bool(bruto, "cifrado", contexto)
        if cifrado:
            blob = bruto.get("conteudo_cifrado")
            if not _blob_valido(blob):
                raise EsquemaInvalidoError(
                    f"{contexto}: nota cifrada sem 'conteudo_cifrado' valido")
            return File(id=id_, nome=nome, criado_em=criado, atualizado_em=atualizado,
                        conteudo=None, cifrado=True,
                        blob={"nonce": blob["nonce"], "ct": blob["ct"]})
        return File(
            id=id_,
            nome=nome,
            criado_em=criado,
            atualizado_em=atualizado,
            conteudo=_texto(bruto, "conteudo", contexto),
        )

    if _bool(bruto, "cifrada", contexto):
        blob = bruto.get("filhos_cifrados")
        if not _blob_valido(blob):
            raise EsquemaInvalidoError(
                f"{contexto}: pasta cifrada sem 'filhos_cifrados' valido")
        return Folder(id=id_, nome=nome, criado_em=criado, atualizado_em=atualizado,
                      cifrada=True, filhos=None,
                      blob={"nonce": blob["nonce"], "ct": blob["ct"]})

    filhos_brutos = bruto.get("filhos", [])
    if not isinstance(filhos_brutos, list):
        raise EsquemaInvalidoError(f"{contexto}: 'filhos' deveria ser uma lista")

    return Folder(
        id=id_,
        nome=nome,
        criado_em=criado,
        atualizado_em=atualizado,
        descricao=_texto(bruto, "descricao", contexto),
        nasce_cifrada=_bool(bruto, "nasce_cifrada", contexto),
        filhos=[node_from_dict(f, reparos) for f in filhos_brutos],
    )


def nova_raiz():
    """Folder raiz de uma base vazia. A raiz e um Folder real, nao lista solta."""
    return Folder(id=ID_RAIZ, nome="KeyBase")
