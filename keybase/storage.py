"""Persistencia da arvore: carga, save atomico, backups e versionamento.

Regra de camada: este modulo NAO importa nada de ui/, nao imprime nada, e
sinaliza falha por excecao. Quem chama decide o que mostrar. (Na versao
anterior salvar_dados() escrevia na area de saida, o que o tornava inutilizavel
num handler de fechamento de janela, com o widget ja destruido.)

Regra de dados: carregar NUNCA inventa dados, exceto quando o arquivo nao
existe. Na versao anterior um JSON corrompido virava silenciosamente uma base
vazia, e o primeiro save escrevia o vazio por cima - perda total.
"""

import hashlib
import json
import os
import time
from datetime import date
from pathlib import Path

from . import model
from .model import EsquemaInvalidoError, Folder, node_from_dict, nova_raiz

SCHEMA_VERSION = 2  # 1 = formato legado plano (programas/atalhos/notas/snippets)
APP_VERSION = "2.0.0"

MAX_SNAPSHOTS = 7
_RETRIES_REPLACE = 3
_ESPERA_REPLACE = 0.05


class StorageError(Exception):
    """Base de todas as falhas de persistencia."""


class DadosCorrompidosError(StorageError):
    def __init__(self, caminho, linha=None, coluna=None):
        self.caminho = caminho
        self.linha = linha
        self.coluna = coluna
        onde = f" na linha {linha}" if linha else ""
        super().__init__(f"JSON invalido{onde} em {caminho}")


class VersaoFuturaError(StorageError):
    def __init__(self, versao):
        self.versao = versao
        super().__init__(
            f"arquivo gravado por uma versao mais nova do KeyBase "
            f"(schema {versao}, esta build entende ate {SCHEMA_VERSION})"
        )


class StorageBloqueadoError(StorageError):
    """Tentativa de escrever em modo recuperacao (somente leitura)."""


# Migracoes registradas num dict literal, com import estatico - carga dinamica
# quebraria a analise do PyInstaller.
MIGRACOES = {}


def _hash(payload):
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


class Documento:
    """A arvore carregada, mais o estado de persistencia."""

    def __init__(self, raiz, somente_leitura=False, avisos=None):
        self.raiz = raiz
        self.somente_leitura = somente_leitura
        self.avisos = avisos or []
        self.sujo = False
        self._hash_persistido = None
        self._em_transacao = False

    @classmethod
    def novo(cls):
        return cls(nova_raiz())

    def to_dict(self):
        return {
            "schema_version": SCHEMA_VERSION,
            "app_version": APP_VERSION,
            "atualizado_em": model.agora_iso(),
            "raiz": self.raiz.to_dict(),
        }

    def marcar_sujo(self):
        self.sujo = True

    def transacao(self):
        return _Transacao(self)


class _Transacao:
    """Agrupa mutacoes para nao persistir estados intermediarios."""

    def __init__(self, doc):
        self.doc = doc

    def __enter__(self):
        self.doc._em_transacao = True
        return self.doc

    def __exit__(self, exc_type, exc, tb):
        self.doc._em_transacao = False
        return False  # nao suprime excecao; sem save se levantou


# --- carga -----------------------------------------------------------------

def carregar(caminho):
    """Le o arquivo de dados. Levanta StorageError em qualquer anomalia."""
    caminho = Path(caminho)
    if not caminho.exists():
        return Documento.novo()  # primeira execucao: unico caso de criar vazio

    texto = caminho.read_text(encoding='utf-8')
    try:
        bruto = json.loads(texto)
    except json.JSONDecodeError as e:
        raise DadosCorrompidosError(caminho, e.lineno, e.colno) from e

    if not isinstance(bruto, dict):
        raise EsquemaInvalidoError("raiz do arquivo deveria ser um objeto JSON")

    bruto = _migrar(bruto)

    if "raiz" not in bruto:
        raise EsquemaInvalidoError("arquivo sem a chave 'raiz'")

    reparos = []
    raiz = node_from_dict(bruto["raiz"], reparos)
    if not isinstance(raiz, Folder):
        raise EsquemaInvalidoError("a raiz precisa ser um folder")

    doc = Documento(raiz, avisos=reparos)
    doc._hash_persistido = _hash(json.dumps(doc.to_dict(), indent=4, ensure_ascii=False))
    if reparos:
        doc.sujo = True
        doc._hash_persistido = None  # forca gravar os reparos
    return doc


def _migrar(bruto):
    versao = bruto.get("schema_version")
    if not isinstance(versao, int):
        raise EsquemaInvalidoError("'schema_version' ausente ou nao inteiro")
    if versao > SCHEMA_VERSION:
        raise VersaoFuturaError(versao)
    while versao < SCHEMA_VERSION:
        migracao = MIGRACOES.get(versao)
        if migracao is None:
            raise EsquemaInvalidoError(
                f"nao ha migracao do schema {versao} para {versao + 1}"
            )
        bruto = migracao(bruto)
        versao += 1
    return bruto


# --- gravacao --------------------------------------------------------------

def salvar(doc, caminho):
    """Grava a arvore de forma atomica. No-op quando nada mudou."""
    if doc.somente_leitura:
        raise StorageBloqueadoError(
            "o documento esta em modo recuperacao; nenhuma escrita e permitida"
        )

    caminho = Path(caminho)
    payload = json.dumps(doc.to_dict(), indent=4, ensure_ascii=False)

    # O hash ignora o campo atualizado_em do cabecalho, que muda a cada chamada.
    assinatura = _hash(json.dumps(
        {"schema_version": SCHEMA_VERSION, "raiz": doc.raiz.to_dict()},
        indent=4, ensure_ascii=False,
    ))
    if assinatura == doc._hash_persistido:
        doc.sujo = False
        return False

    tmp = caminho.with_name(caminho.name + '.tmp')
    caminho.parent.mkdir(parents=True, exist_ok=True)

    # newline='\n' para o arquivo nao inchar com CRLF no Windows.
    with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
        f.write(payload)
        f.flush()
        os.fsync(f.fileno())

    _rotacionar_backups(caminho)
    _replace_com_retry(tmp, caminho)

    doc._hash_persistido = assinatura
    doc.sujo = False
    return True


def salvar_se_sujo(doc, caminho):
    """Usado no handler de fechamento da janela. Nunca levanta."""
    try:
        if doc.sujo and not doc.somente_leitura:
            salvar(doc, caminho)
    except (StorageError, OSError):
        pass


def _replace_com_retry(origem, destino):
    """os.replace e atomico e sobrescreve; os.rename falharia no Windows.

    Antivirus e indexador do Windows travam arquivos por dezenas de ms - o
    retry aqui e o modo de falha realista deste app, nao paranoia.
    """
    ultimo_erro = None
    for tentativa in range(_RETRIES_REPLACE):
        try:
            os.replace(origem, destino)
            return
        except OSError as e:
            ultimo_erro = e
            if tentativa < _RETRIES_REPLACE - 1:
                time.sleep(_ESPERA_REPLACE)
    raise StorageError(
        f"nao foi possivel gravar {destino} apos {_RETRIES_REPLACE} tentativas: {ultimo_erro}"
    ) from ultimo_erro


def caminho_backup(caminho):
    caminho = Path(caminho)
    return caminho.with_name(caminho.stem + '.bak' + caminho.suffix)


def caminho_snapshot(caminho, dia=None):
    caminho = Path(caminho)
    dia = dia or date.today().isoformat()
    return caminho.with_name(f'{caminho.stem}.snapshot-{dia}{caminho.suffix}')


def _rotacionar_backups(caminho):
    """Copia a versao atual para .bak e, uma vez por dia, para um snapshot."""
    caminho = Path(caminho)
    if not caminho.exists():
        return
    conteudo = caminho.read_bytes()

    caminho_backup(caminho).write_bytes(conteudo)

    snapshot = caminho_snapshot(caminho)
    if not snapshot.exists():
        snapshot.write_bytes(conteudo)
        _podar_snapshots(caminho)


def _podar_snapshots(caminho):
    caminho = Path(caminho)
    padrao = f'{caminho.stem}.snapshot-*{caminho.suffix}'
    existentes = sorted(caminho.parent.glob(padrao))
    for antigo in existentes[:-MAX_SNAPSHOTS]:
        try:
            antigo.unlink()
        except OSError:
            pass


def snapshot(doc, caminho):
    """Forca um .bak antes de uma operacao destrutiva.

    E isto que torna o backup o 'undo' real do v1, em vez de decorativo.
    """
    caminho = Path(caminho)
    if caminho.exists():
        caminho_backup(caminho).write_bytes(caminho.read_bytes())


def backups_disponiveis(caminho):
    """Lista (rotulo, caminho) dos backups restauraveis, mais recente primeiro."""
    caminho = Path(caminho)
    achados = []
    bak = caminho_backup(caminho)
    if bak.exists():
        achados.append((_rotulo_mtime('Backup anterior', bak), bak))
    padrao = f'{caminho.stem}.snapshot-*{caminho.suffix}'
    for snap in sorted(caminho.parent.glob(padrao), reverse=True):
        dia = snap.stem.split('snapshot-')[-1]
        achados.append((f'Snapshot de {dia}', snap))
    return achados


def _rotulo_mtime(prefixo, arquivo):
    from datetime import datetime
    quando = datetime.fromtimestamp(arquivo.stat().st_mtime)
    return f'{prefixo} ({quando.strftime("%d/%m/%Y %H:%M")})'


def restaurar(origem, destino):
    """Copia um backup por cima do arquivo de dados, de forma atomica."""
    origem, destino = Path(origem), Path(destino)
    tmp = destino.with_name(destino.name + '.tmp')
    tmp.write_bytes(origem.read_bytes())
    _replace_com_retry(tmp, destino)
