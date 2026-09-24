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

from . import cripto, model
from .model import EsquemaInvalidoError, Folder, node_from_dict, nova_raiz

# 1 = formato legado plano (programas/atalhos/notas/snippets)
# 3 = notas cifradas. O salto e o que protege os dados: uma build de schema 2
#     ignoraria 'conteudo_cifrado', leria a nota como vazia e gravaria por cima.
# 4 = pastas inteiramente cifradas. Mesmo motivo: uma build de schema 3 leria
#     a pasta sem 'filhos' como vazia e gravaria o vazio por cima.
SCHEMA_VERSION = 4
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


class ConflitoError(StorageError):
    """O arquivo em disco mudou por fora desde a ultima leitura ou gravacao.

    O caso realista: a pasta de dados sincronizada (iCloud, Dropbox, Drive) e
    outro computador gravou. Sobrescrever apagaria o trabalho de la em
    silencio; quem chama decide (recarregar, ou salvar com forcar=True).
    """

    def __init__(self, caminho):
        self.caminho = caminho
        super().__init__(f"{Path(caminho).name} foi alterado fora deste KeyBase")


def _migrar_2_para_3(bruto):
    """Schema 3 so acrescenta campos opcionais: nada a converter."""
    return bruto


def _migrar_3_para_4(bruto):
    """Schema 4 so acrescenta campos opcionais: nada a converter."""
    return bruto


# Migracoes registradas num dict literal, com import estatico - carga dinamica
# quebraria a analise do PyInstaller.
MIGRACOES = {2: _migrar_2_para_3, 3: _migrar_3_para_4}


def _hash(payload):
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


class Documento:
    """A arvore carregada, mais o estado de persistencia."""

    def __init__(self, raiz, somente_leitura=False, avisos=None, cofre=None):
        self.raiz = raiz
        #: cabecalho do cofre (dict) ou None se nenhuma nota foi cifrada ainda
        self.cofre = cofre
        self.somente_leitura = somente_leitura
        self.avisos = avisos or []
        self.sujo = False
        self._hash_persistido = None
        self._em_transacao = False
        #: sha256 do arquivo como lido/gravado por nos; None = ainda nao existia
        self._disco = None

    @classmethod
    def novo(cls):
        return cls(nova_raiz())

    def to_dict(self):
        d = {
            "schema_version": SCHEMA_VERSION,
            "app_version": APP_VERSION,
            "atualizado_em": model.agora_iso(),
        }
        if self.cofre is not None:
            d["cofre"] = self.cofre
        d["raiz"] = self.raiz.to_dict()
        return d

    def assinatura(self):
        """Hash do que importa, sem o atualizado_em do cabecalho."""
        return _hash(json.dumps(
            {"schema_version": SCHEMA_VERSION, "cofre": self.cofre,
             "raiz": self.raiz.to_dict()},
            indent=4, ensure_ascii=False,
        ))

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

    conteudo = caminho.read_bytes()
    texto = conteudo.decode('utf-8')
    try:
        bruto = json.loads(texto)
    except json.JSONDecodeError as e:
        raise DadosCorrompidosError(caminho, e.lineno, e.colno) from e

    if not isinstance(bruto, dict):
        raise EsquemaInvalidoError("raiz do arquivo deveria ser um objeto JSON")

    bruto = _migrar(bruto)

    if "raiz" not in bruto:
        raise EsquemaInvalidoError("arquivo sem a chave 'raiz'")

    cofre = bruto.get("cofre")
    if cofre is not None and not cripto.validar_meta(cofre):
        raise EsquemaInvalidoError("cabecalho 'cofre' invalido")

    reparos = []
    raiz = node_from_dict(bruto["raiz"], reparos)
    if not isinstance(raiz, Folder):
        raise EsquemaInvalidoError("a raiz precisa ser um folder")
    if cofre is None and cripto.tem_cifra(raiz):
        raise EsquemaInvalidoError("ha itens cifrados, mas o arquivo nao tem 'cofre'")

    doc = Documento(raiz, avisos=reparos, cofre=cofre)
    doc._disco = hashlib.sha256(conteudo).hexdigest()
    doc._hash_persistido = doc.assinatura()
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

def _impressao_do_disco(caminho):
    try:
        return hashlib.sha256(Path(caminho).read_bytes()).hexdigest()
    except FileNotFoundError:
        return None


def salvar(doc, caminho, forcar=False):
    """Grava a arvore de forma atomica. No-op quando nada mudou.

    Levanta ConflitoError se o arquivo mudou por fora desde que o lemos (ou
    gravamos), a menos que forcar=True. O .bak ainda guarda a versao de fora.
    """
    if doc.somente_leitura:
        raise StorageBloqueadoError(
            "o documento esta em modo recuperacao; nenhuma escrita e permitida"
        )

    caminho = Path(caminho)
    payload = json.dumps(doc.to_dict(), indent=4, ensure_ascii=False)

    # O hash ignora o campo atualizado_em do cabecalho, que muda a cada chamada.
    assinatura = doc.assinatura()
    if assinatura == doc._hash_persistido:
        doc.sujo = False
        return False

    if not forcar and _impressao_do_disco(caminho) != doc._disco:
        raise ConflitoError(caminho)

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
    doc._disco = hashlib.sha256(payload.encode('utf-8')).hexdigest()
    doc.sujo = False
    return True


def salvar_copia_de_conflito(doc, caminho):
    """Grava a versao da memoria ao lado, sem tocar o arquivo principal.

    Num conflito, e o que garante que escolher 'recarregar o do disco' nao
    perde nada: as mudancas daqui ficam num arquivo que carregar() le.
    """
    from datetime import datetime
    caminho = Path(caminho)
    quando = datetime.now().strftime('%Y-%m-%d-%H%M%S')
    copia = caminho.with_name(f'{caminho.stem}.conflito-{quando}{caminho.suffix}')
    tmp = copia.with_name(copia.name + '.tmp')
    with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(doc.to_dict(), indent=4, ensure_ascii=False))
        f.flush()
        os.fsync(f.fileno())
    _replace_com_retry(tmp, copia)
    return copia


def salvar_se_sujo(doc, caminho):
    """Usado no handler de fechamento da janela. Nunca levanta.

    Num conflito, as mudancas vao para a copia de conflito em vez de sumir.
    """
    try:
        if doc.sujo and not doc.somente_leitura:
            salvar(doc, caminho)
    except ConflitoError:
        try:
            salvar_copia_de_conflito(doc, caminho)
        except (StorageError, OSError):
            pass
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


# --- backups com texto claro -----------------------------------------------

def _arquivos_de_backup(caminho):
    return [arquivo for _, arquivo in backups_disponiveis(caminho)]


def _nos_claros(no_bruto, ids, achados):
    """Dicts de nota ou pasta, num JSON bruto, com esses ids e ainda em claro.

    Uma pasta achada nao e percorrida: ela sera cifrada inteira, com tudo dentro.
    """
    if not isinstance(no_bruto, dict):
        return achados
    em_alvo = no_bruto.get("id") in ids
    if no_bruto.get("tipo") == "file":
        if (em_alvo and not no_bruto.get("cifrado")
                and isinstance(no_bruto.get("conteudo"), str)):
            achados.append(no_bruto)
        return achados
    filhos = no_bruto.get("filhos")
    if em_alvo and not no_bruto.get("cifrada") and isinstance(filhos, list):
        achados.append(no_bruto)
        return achados
    for filho in filhos or []:
        _nos_claros(filho, ids, achados)
    return achados


def _cifrar_no_bruto(no, cofre):
    """Troca, no proprio dict, o texto claro pelo blob - nota ou pasta."""
    if no.get("tipo") == "file":
        no["conteudo_cifrado"] = cofre.cifrar(no.pop("conteudo"), no["id"])
        no["cifrado"] = True
        return
    payload = model.payload_pasta(no.pop("descricao", ""), no.pop("filhos"))
    no.pop("nasce_cifrada", None)
    no["filhos_cifrados"] = cofre.cifrar(payload, no["id"])
    no["cifrada"] = True


def _ler_backup(arquivo):
    """JSON bruto de um backup, ou None se ilegivel - backup ruim nao trava nada."""
    try:
        bruto = json.loads(Path(arquivo).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    return bruto if isinstance(bruto, dict) and isinstance(bruto.get("raiz"), dict) else None


def backups_com_texto_claro(caminho, ids):
    """Backups (.bak e snapshots) que ainda guardam alguma dessas notas ou
    pastas em claro."""
    ids = set(ids)
    achados = []
    for arquivo in _arquivos_de_backup(caminho):
        bruto = _ler_backup(arquivo)
        if bruto is not None and _nos_claros(bruto["raiz"], ids, []):
            achados.append(arquivo)
    return achados


def sanear_backups(caminho, cofre, ids):
    """Cifra, dentro dos backups, as notas e pastas desses ids ainda em claro.

    Cada uma e cifrada com o PROPRIO conteudo antigo, entao o historico dos
    snapshots continua valendo - so deixa de estar legivel sem a senha. O
    backup passa ao schema atual e ganha o cabecalho do cofre, como o arquivo
    atual. Devolve quantos arquivos foram regravados.
    """
    ids = set(ids)
    regravados = 0
    for arquivo in _arquivos_de_backup(caminho):
        bruto = _ler_backup(arquivo)
        if bruto is None:
            continue
        nos = _nos_claros(bruto["raiz"], ids, [])
        if not nos:
            continue
        for no in nos:
            _cifrar_no_bruto(no, cofre)
        bruto["schema_version"] = SCHEMA_VERSION
        bruto["cofre"] = cofre.to_dict()

        arquivo = Path(arquivo)
        tmp = arquivo.with_name(arquivo.name + '.tmp')
        with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps(bruto, indent=4, ensure_ascii=False))
            f.flush()
            os.fsync(f.fileno())
        _replace_com_retry(tmp, arquivo)
        regravados += 1
    return regravados
