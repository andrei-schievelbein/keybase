"""Cofre de notas cifradas: senha mestra, chave de dados e AES-256-GCM.

Sem Qt e sem I/O - o cofre so transforma texto em blob e vice-versa. Quem
grava e o storage; quem pede a senha e a UI.

Esquema de envelope: uma chave de dados (DEK) aleatoria cifra as notas, e a
propria DEK fica gravada cifrada por uma chave derivada da senha (KEK, via
scrypt). Trocar a senha, ou acrescentar outro jeito de destravar no futuro,
so reenvelopa a DEK - nenhuma nota precisa ser recifrada.

O id da nota entra como dado associado (AAD) do GCM: um blob copiado para
outra nota nao decifra, em vez de aparecer em silencio no lugar errado.
"""

import base64
import hashlib
import json
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .model import File, Folder, _blob_valido as blob_valido, node_from_dict

VERSAO_COFRE = 1
# scrypt com N=2^17 custa ~128 MB e uma fracao de segundo: pesa so no destravar,
# que acontece uma vez por sessao.
SCRYPT_N = 2 ** 17
SCRYPT_R = 8
SCRYPT_P = 1
_TAM_CHAVE = 32
_TAM_SALT = 16
_TAM_NONCE = 12
_AAD_DEK = b"keybase-dek"


class CriptoError(Exception):
    """Base das falhas do cofre."""


class SenhaIncorretaError(CriptoError):
    pass


class CofreTrancadoError(CriptoError):
    """Operacao que precisa da DEK com o cofre trancado."""


class BlobInvalidoError(CriptoError):
    """Blob adulterado, truncado ou de outra nota."""


def _b64(dados):
    return base64.b64encode(dados).decode('ascii')


def _de_b64(texto):
    return base64.b64decode(texto.encode('ascii'), validate=True)


def _derivar(senha, salt, n, r, p):
    return hashlib.scrypt(senha.encode('utf-8'), salt=salt, n=n, r=r, p=p,
                          maxmem=256 * 1024 * 1024, dklen=_TAM_CHAVE)


def _selar(chave, dados, aad):
    nonce = os.urandom(_TAM_NONCE)
    ct = AESGCM(chave).encrypt(nonce, dados, aad)
    return {"nonce": _b64(nonce), "ct": _b64(ct)}


def _abrir(chave, blob, aad):
    try:
        nonce = _de_b64(blob["nonce"])
        ct = _de_b64(blob["ct"])
    except (KeyError, TypeError, ValueError) as e:
        raise BlobInvalidoError("blob cifrado malformado") from e
    return AESGCM(chave).decrypt(nonce, ct, aad)  # InvalidTag fica com quem chama


class Cofre:
    """Metadados do cofre (gravados no arquivo) mais a DEK, so em memoria."""

    def __init__(self, meta):
        self.meta = meta
        self._dek = None

    @staticmethod
    def _envelope(senha, dek):
        """Cabecalho do cofre: a DEK cifrada pela senha, com salt novo."""
        salt = os.urandom(_TAM_SALT)
        kek = _derivar(senha, salt, SCRYPT_N, SCRYPT_R, SCRYPT_P)
        return {
            "v": VERSAO_COFRE,
            "kdf": "scrypt",
            "n": SCRYPT_N, "r": SCRYPT_R, "p": SCRYPT_P,
            "salt": _b64(salt),
            "dek": _selar(kek, dek, _AAD_DEK),
        }

    @classmethod
    def criar(cls, senha):
        """Cofre novo, ja destravado."""
        dek = AESGCM.generate_key(bit_length=_TAM_CHAVE * 8)
        cofre = cls(cls._envelope(senha, dek))
        cofre._dek = dek
        return cofre

    @classmethod
    def from_dict(cls, meta):
        return cls(dict(meta))

    def to_dict(self):
        return dict(self.meta)

    @property
    def destravado(self):
        return self._dek is not None

    def destravar(self, senha):
        m = self.meta
        kek = _derivar(senha, _de_b64(m["salt"]), m["n"], m["r"], m["p"])
        try:
            self._dek = _abrir(kek, m["dek"], _AAD_DEK)
        except InvalidTag as e:
            raise SenhaIncorretaError("senha incorreta") from e

    def trancar(self):
        self._dek = None

    def conferir(self, senha):
        """True se a senha abre a DEK. Nao muda o estado (trancado segue trancado)."""
        m = self.meta
        kek = _derivar(senha, _de_b64(m["salt"]), m["n"], m["r"], m["p"])
        try:
            _abrir(kek, m["dek"], _AAD_DEK)
        except InvalidTag:
            return False
        return True

    def trocar_senha(self, atual, nova):
        """Reenvelopa a MESMA DEK com a senha nova e um salt novo.

        Nenhuma nota e recifrada: e o motivo do envelope. Copias antigas do
        cabecalho (backups, snapshots) continuam abrindo com a senha antiga.
        O estado trancado/destravado e preservado.
        """
        m = self.meta
        kek = _derivar(atual, _de_b64(m["salt"]), m["n"], m["r"], m["p"])
        try:
            dek = _abrir(kek, m["dek"], _AAD_DEK)
        except InvalidTag as e:
            raise SenhaIncorretaError("senha incorreta") from e
        self.meta = self._envelope(nova, dek)

    def _exigir_dek(self):
        if self._dek is None:
            raise CofreTrancadoError("o cofre esta trancado")
        return self._dek

    def cifrar(self, texto, aad):
        return _selar(self._exigir_dek(), texto.encode('utf-8'), aad.encode('utf-8'))

    def decifrar(self, blob, aad):
        try:
            dados = _abrir(self._exigir_dek(), blob, aad.encode('utf-8'))
        except InvalidTag as e:
            raise BlobInvalidoError("blob adulterado ou de outra nota") from e
        return dados.decode('utf-8')


def validar_meta(meta):
    """True se o dict tem a forma de um cabecalho de cofre que sabemos ler."""
    if not isinstance(meta, dict) or meta.get("v") != VERSAO_COFRE:
        return False
    if meta.get("kdf") != "scrypt":
        return False
    if not all(isinstance(meta.get(k), int) for k in ("n", "r", "p")):
        return False
    return isinstance(meta.get("salt"), str) and blob_valido(meta.get("dek"))


# --- operacoes sobre a arvore ----------------------------------------------

def _filhos_visiveis(folder):
    """Filhos de uma pasta, ou nada se ela esta trancada."""
    return folder.filhos if folder.filhos is not None else ()


def notas_cifradas(no):
    """Notas cifradas da subarvore visivel (inclui o proprio no se for nota)."""
    if isinstance(no, File):
        return [no] if no.cifrado else []
    achadas = []
    for filho in _filhos_visiveis(no):
        achadas.extend(notas_cifradas(filho))
    return achadas


def notas_em_claro(no):
    """Notas ainda nao cifradas da subarvore - alvo do 'cifrar notas da pasta'."""
    if isinstance(no, File):
        return [] if no.cifrado else [no]
    achadas = []
    for filho in _filhos_visiveis(no):
        achadas.extend(notas_em_claro(filho))
    return achadas


def pastas_cifradas(no):
    """Pastas inteiramente cifradas da subarvore visivel, de cima para baixo."""
    if not isinstance(no, Folder):
        return []
    achadas = [no] if no.cifrada else []
    for filho in _filhos_visiveis(no):
        achadas.extend(pastas_cifradas(filho))
    return achadas


def tem_cifra(raiz):
    """True se ha qualquer coisa cifrada na arvore (nota ou pasta)."""
    return bool(notas_cifradas(raiz) or pastas_cifradas(raiz))


def pasta_cifrada_na_cadeia(cadeia):
    """A pasta cifrada mais externa num caminho raiz->no, ou None.

    Tudo abaixo dela ja esta protegido: cifrar de novo seria cifra dentro de cifra.
    """
    for no in cadeia:
        if isinstance(no, Folder) and no.cifrada:
            return no
    return None


# --- pastas inteiramente cifradas ------------------------------------------

def selar_pasta(cofre, pasta):
    """Recifra descricao e filhos de uma pasta cifrada aberta, se mudaram."""
    if pasta.trancada:
        return
    payload = pasta.payload()
    if payload == pasta.selado:
        return
    pasta.blob = cofre.cifrar(payload, pasta.id)
    pasta.selado = payload


def selar_pastas(raiz, cofre):
    """Chamada antes de todo save: nenhuma pasta aberta vai para o disco velha."""
    for pasta in pastas_cifradas(raiz):
        if not pasta.trancada:
            selar_pasta(cofre, pasta)


def abrir_pasta(cofre, pasta):
    """Decifra descricao e filhos para a memoria."""
    if not pasta.trancada:
        return
    try:
        dados = json.loads(cofre.decifrar(pasta.blob, pasta.id))
    except ValueError as e:
        raise BlobInvalidoError(f"conteudo da pasta {pasta.nome!r} ilegivel") from e
    pasta.descricao = dados.get("descricao", "")
    pasta.filhos = [node_from_dict(f) for f in dados.get("filhos", [])]
    pasta.selado = pasta.payload()


def fechar_pasta(pasta):
    """Esquece o conteudo. Exige a pasta ja selada - o blob e a unica copia."""
    if pasta.trancada:
        return
    if pasta.payload() != pasta.selado:
        raise CriptoError(f"pasta {pasta.nome!r} precisa ser selada antes de fechar")
    pasta.filhos = None
    pasta.descricao = ""
    pasta.selado = None


def cifrar_pasta(cofre, pasta):
    """Passa uma pasta comum para inteiramente cifrada.

    Notas ja cifradas dentro dela sao decifradas (sem cifra dentro de cifra) e
    'nasce_cifrada' e desligado na subarvore: dentro dela tudo ja e protegido.
    """
    for nota in notas_cifradas(pasta):
        decifrar_nota(cofre, nota)
    for sub in _todas_as_pastas(pasta):
        sub.nasce_cifrada = False
    pasta.cifrada = True
    pasta.selado = None
    selar_pasta(cofre, pasta)
    pasta.touch()


def absorver_em_pasta_cifrada(cofre, no):
    """Prepara um no que entra (movido ou duplicado) numa pasta cifrada.

    Dentro dela tudo ja e protegido: notas e pastas cifradas do no voltam a ser
    comuns, e 'nasce_cifrada' e desligado - as mesmas regras de cifrar_pasta.
    Exige o cofre destravado (as pastas cifradas do no precisam estar abertas).
    """
    if isinstance(no, File):
        decifrar_nota(cofre, no)
        return
    for nota in notas_cifradas(no):
        decifrar_nota(cofre, nota)
    for pasta in pastas_cifradas(no):
        decifrar_pasta(pasta)
    for sub in _todas_as_pastas(no):
        sub.nasce_cifrada = False


def selar_copia(cofre, copia):
    """Recifra, com os ids novos, o que era cifrado numa copia (tree.copia_profunda).

    Notas primeiro, pastas de dentro para fora: o blob de uma pasta de fora
    tem de conter o blob ja pronto das de dentro.
    """
    for nota in notas_cifradas(copia):
        nota.blob = cofre.cifrar(nota.conteudo or "", nota.id)
    for pasta in reversed(pastas_cifradas(copia)):
        pasta.selado = None
        selar_pasta(cofre, pasta)


def precisa_do_cofre(no):
    """Duplicar isto exige o cofre aberto? (algo cifrado dentro, ou trancado)"""
    if isinstance(no, File):
        return no.cifrado
    return no.trancada or tem_cifra(no)


def decifrar_pasta(pasta):
    """Volta a pasta (aberta) para comum: filhos e descricao em claro no disco."""
    if pasta.trancada:
        raise CofreTrancadoError("abra a pasta antes de decifrar")
    pasta.cifrada = False
    pasta.blob = None
    pasta.selado = None
    pasta.touch()


def _todas_as_pastas(pasta):
    pastas = [pasta]
    for filho in _filhos_visiveis(pasta):
        if isinstance(filho, Folder):
            pastas.extend(_todas_as_pastas(filho))
    return pastas


# --- destravar e trancar a arvore inteira ----------------------------------

def destravar_arvore(raiz, cofre):
    """Abre as pastas cifradas e decifra as notas cifradas, tudo para memoria."""
    for pasta in pastas_cifradas(raiz):
        abrir_pasta(cofre, pasta)
    for nota in notas_cifradas(raiz):
        if nota.conteudo is None:
            nota.conteudo = cofre.decifrar(nota.blob, nota.id)


def trancar_arvore(raiz, cofre=None):
    """Esquece o texto claro. O blob continua sendo a verdade em disco.

    Com `cofre` (ainda destravado), sela as pastas abertas antes de fecha-las.
    """
    for nota in notas_cifradas(raiz):
        nota.conteudo = None
    for pasta in reversed(pastas_cifradas(raiz)):
        if cofre is not None and cofre.destravado:
            selar_pasta(cofre, pasta)
        fechar_pasta(pasta)


def cifrar_nota(cofre, nota):
    """Passa uma nota em claro para cifrada. Nao muda o texto em memoria."""
    if nota.cifrado:
        return
    nota.blob = cofre.cifrar(nota.conteudo or "", nota.id)
    nota.cifrado = True
    nota.touch()


def decifrar_nota(cofre, nota):
    """Volta uma nota cifrada para texto claro em disco."""
    if not nota.cifrado:
        return
    if nota.conteudo is None:
        nota.conteudo = cofre.decifrar(nota.blob, nota.id)
    nota.cifrado = False
    nota.blob = None
    nota.touch()


def selar(cofre, nota, texto):
    """Grava texto novo numa nota cifrada.

    Recifra so quando o texto muda: um nonce novo a cada save mudaria o blob,
    e o save "nada mudou" do storage deixaria de ser no-op.
    """
    if texto == nota.conteudo:
        return
    nota.blob = cofre.cifrar(texto, nota.id)
    nota.conteudo = texto
    nota.touch()


def pasta_nasce_cifrada(folder):
    return isinstance(folder, Folder) and folder.nasce_cifrada
