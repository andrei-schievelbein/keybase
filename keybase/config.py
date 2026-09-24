"""Configuracao do usuario (keybase_config.toml) e estado da janela.

Dois arquivos, porque tem dois donos:

- keybase_config.toml e do USUARIO. Editado com C dentro do app (ou a mao),
  com comentarios. O app so o cria na primeira vez e depois grava exatamente o
  texto que o usuario salvou - nunca o reescreve a partir de um dict, entao
  comentarios e formatacao sobrevivem. Por isso nao ha escritor de TOML aqui.
- keybase_estado.json e do APP: geometria da janela e ultimo modo do editor,
  regravados a cada fechamento.

Lido com tomllib, da biblioteca padrao (Python 3.11+): nenhuma dependencia nova.

Por dentro o config continua um dict com as chaves de sempre ('theme',
'fonts', 'interface', 'cofre', 'geometry', 'editor'); o esquema abaixo so
traduz as chaves em portugues do TOML para elas. Este modulo nao importa Qt.
"""

import json
import os
import re
import tomllib
from pathlib import Path

from .paths import arquivo_config, arquivo_config_legado, arquivo_estado

TEMAS = ('dark', 'light')


class Campo:
    """Uma chave do TOML: onde mora por dentro, padrao e como validar."""

    def __init__(self, secao, chave, interno, padrao, validar):
        self.secao = secao          # None = topo do arquivo
        self.chave = chave
        self.interno = interno      # ('fonts', 'family') ou ('theme',)
        self.padrao = padrao
        self.validar = validar      # valor -> mensagem de erro ou None

    @property
    def rotulo(self):
        return f"{self.secao}.{self.chave}" if self.secao else self.chave


def _texto(valor):
    if not isinstance(valor, str) or not valor.strip():
        return "deveria ser um texto entre aspas, não vazio"
    return None


def _inteiro(minimo, maximo=None):
    def validar(valor):
        # bool e subclasse de int em Python: true/false nao pode passar por numero
        if isinstance(valor, bool) or not isinstance(valor, int):
            return "deveria ser um número inteiro"
        if valor < minimo or (maximo is not None and valor > maximo):
            faixa = f"entre {minimo} e {maximo}" if maximo is not None else f"a partir de {minimo}"
            return f"deveria ser {faixa}"
        return None
    return validar


def _pasta(valor):
    if not isinstance(valor, str):
        return 'deveria ser um texto entre aspas ("" para a pasta padrão)'
    if valor and not Path(valor).expanduser().is_dir():
        return "deveria ser uma pasta que existe"
    return None


def _texto_ou_vazio(valor):
    if not isinstance(valor, str):
        return 'deveria ser um texto entre aspas ("" desliga)'
    return None


def _tema(valor):
    if valor not in TEMAS:
        return 'deveria ser "dark" ou "light"'
    return None


ESQUEMA = (
    Campo(None, 'tema', ('theme',), 'dark', _tema),
    Campo('fontes', 'familia', ('fonts', 'family'), 'Consolas', _texto),
    Campo('fontes', 'alternativa', ('fonts', 'fallback'), 'Courier New', _texto),
    Campo('fontes', 'tamanho_entrada', ('fonts', 'input_size'), 12, _inteiro(6, 72)),
    Campo('fontes', 'tamanho_saida', ('fonts', 'output_size'), 14, _inteiro(6, 72)),
    Campo('fontes', 'tamanho_ajuda', ('fonts', 'help_size'), 12, _inteiro(6, 72)),
    Campo('interface', 'altura_ajuda', ('interface', 'help_area_height'), 60,
          _inteiro(0, 400)),
    Campo('interface', 'tempo_aviso_ms', ('interface', 'flash_ms'), 2500,
          _inteiro(500, 30000)),
    Campo('cofre', 'trancar_apos_min', ('cofre', 'auto_lock_min'), 10, _inteiro(0)),
    Campo('cofre', 'limpar_copia_seg', ('cofre', 'clip_seg'), 20, _inteiro(0, 3600)),
    Campo('dados', 'pasta', ('dados', 'pasta'), '', _pasta),
    Campo('notas', 'pasta_modelos', ('notas', 'modelos'), 'Modelos', _texto_ou_vazio),
)

#: o que o app regrava sozinho, fora do TOML
ESTADO_PADRAO = {
    'geometry': '800x600',
    'editor': {'modo': 'editar', 'proporcao': [1, 1]},
    #: ids das ultimas notas abertas - so ids: nome de item dentro de pasta
    #: cifrada nunca vai em claro para este arquivo
    'recentes': [],
}


def _ler(config, caminho):
    for chave in caminho:
        config = config[chave]
    return config


def _escrever(config, caminho, valor):
    for chave in caminho[:-1]:
        config = config.setdefault(chave, {})
    config[caminho[-1]] = valor


def _padrao_usuario():
    config = {}
    for campo in ESQUEMA:
        _escrever(config, campo.interno, campo.padrao)
    return config


def _padrao_completo():
    config = _padrao_usuario()
    config.update(json.loads(json.dumps(ESTADO_PADRAO)))  # copia profunda
    return config


#: config completo com os padroes - base dos testes e do modo "config invalida"
DEFAULT_CONFIG = _padrao_completo()


# --- modelo do arquivo -----------------------------------------------------

def _toml(valor):
    """Valor TOML de um str/int. json.dumps de str e uma string TOML basica."""
    return json.dumps(valor, ensure_ascii=False) if isinstance(valor, str) else str(valor)


def modelo_toml(config=None):
    """O texto do keybase_config.toml, com comentarios, a partir de um config."""
    config = config or _padrao_usuario()

    def v(*caminho):
        return _toml(_ler(config, caminho))

    return f'''# KeyBase - configuração
# Edite com C dentro do app. Ctrl+S valida, salva e aplica.
# Linhas começando com # são comentários.

# Tema: "dark" (escuro) ou "light" (claro). Aplica na hora.
tema = {v('theme')}

[fontes]
# Vale ao reabrir o KeyBase. Prefira fontes monoespaçadas:
# "Consolas", "Courier New", "Roboto Mono", "Fira Code"
familia = {v('fonts', 'family')}
alternativa = {v('fonts', 'fallback')}
# Tamanhos em pixels
tamanho_entrada = {v('fonts', 'input_size')}
tamanho_saida = {v('fonts', 'output_size')}
tamanho_ajuda = {v('fonts', 'help_size')}

[interface]
# Altura mínima da barra de ajuda, em pixels. Aplica na hora.
altura_ajuda = {v('interface', 'help_area_height')}
# Quanto tempo um aviso ("Pasta criada.", "Itens cifrados trancados.") fica no
# lugar do caminho antes de sumir, em milissegundos (2500 = 2,5 s). Aplica na hora.
tempo_aviso_ms = {v('interface', 'flash_ms')}

[cofre]
# Minutos sem uso até os itens cifrados trancarem sozinhos (0 desliga).
trancar_apos_min = {v('cofre', 'auto_lock_min')}
# Ao copiar (Y) algo cifrado, segundos até a área de transferência ser limpa
# (0 não limpa). Só limpa se ela ainda tiver o que foi copiado. Aplica na hora.
limpar_copia_seg = {v('cofre', 'clip_seg')}

[dados]
# Pasta onde ficam keybase_data.json e os backups. "" = ao lado do programa.
# Aponte para uma pasta do iCloud, Dropbox ou Google Drive para usar os mesmos
# dados em vários computadores. Vale ao reabrir; na primeira vez os dados
# atuais são COPIADOS para lá. No Windows use / nas pastas: "C:/Users/voce/Dropbox"
pasta = {v('dados', 'pasta')}

[notas]
# Pasta da raiz com os modelos de nota: cada nota dela é um modelo. Ao criar
# uma nota com N, o KeyBase oferece os modelos; {{nome}} e {{data}} no texto do
# modelo são preenchidos. "" desliga. Aplica na hora.
pasta_modelos = {v('notas', 'modelos')}
'''


# --- validacao -------------------------------------------------------------

def _erro_de_sintaxe(erro):
    """'linha 3: ...' - o tomllib diz a posicao no fim, em ingles."""
    texto = str(erro)
    achado = re.search(r"\(at line (\d+), column \d+\)", texto)
    if not achado:
        return f"Erro de sintaxe: {texto}. Confira aspas e o sinal ="
    motivo = texto[:achado.start()].strip()
    return (f"Erro de sintaxe na linha {achado.group(1)} ({motivo}). "
            f"Confira aspas e o sinal =")


def validar_texto(texto):
    """(config do usuario, erros). Com erro, o config vem None.

    Chave que falta usa o padrao; chave desconhecida e erro, para pegar erro
    de digitacao ('tamanho_saída') em vez de ignora-lo em silencio.
    """
    try:
        bruto = tomllib.loads(texto)
    except tomllib.TOMLDecodeError as e:
        return None, [_erro_de_sintaxe(e)]

    erros = []
    config = _padrao_usuario()
    conhecidas = {None: set()}
    for campo in ESQUEMA:
        conhecidas.setdefault(campo.secao, set()).add(campo.chave)

    for chave, valor in bruto.items():
        if isinstance(valor, dict):
            if chave not in conhecidas or chave is None:
                erros.append(f"Seção desconhecida: [{chave}]")
                continue
            for sub in valor:
                if sub not in conhecidas[chave]:
                    erros.append(f"Chave desconhecida: {chave}.{sub}")
        elif chave not in conhecidas[None]:
            erros.append(f"Chave desconhecida: {chave}")

    for campo in ESQUEMA:
        secao = bruto.get(campo.secao, {}) if campo.secao else bruto
        if not isinstance(secao, dict) or campo.chave not in secao:
            continue
        erro = campo.validar(secao[campo.chave])
        if erro:
            erros.append(f"{campo.rotulo} {erro}")
        else:
            _escrever(config, campo.interno, secao[campo.chave])

    return (None, erros) if erros else (config, [])


# --- opcoes novas num arquivo antigo ---------------------------------------

def _bloco_do_modelo(campo):
    """Linhas do modelo para um campo: os comentarios logo acima e a chave."""
    linhas = modelo_toml().splitlines()
    secao = None
    for i, linha in enumerate(linhas):
        cabecalho = re.match(r"^\[(\w+)\]\s*$", linha)
        if cabecalho:
            secao = cabecalho.group(1)
            continue
        if secao == campo.secao and re.match(rf"^{campo.chave}\s*=", linha):
            inicio = i
            while inicio > 0 and linhas[inicio - 1].startswith('#'):
                inicio -= 1
            return linhas[inicio:i + 1]
    return [f"{campo.chave} = {_toml(campo.padrao)}"]


def completar_texto(texto):
    """(texto, chaves) - o texto com as opcoes que faltam, no lugar certo.

    Um arquivo criado por uma versao anterior nao tem as opcoes novas, e o app
    nunca reescreve o arquivo do usuario. Entao a tela de configuracao chama
    isto ao abrir: as opcoes que faltam aparecem no EDITOR, com o comentario
    de cada uma, e so vao para o disco se o usuario salvar. Texto invalido
    volta intacto - completar por cima de um erro so confundiria.
    """
    try:
        bruto = tomllib.loads(texto)
    except tomllib.TOMLDecodeError:
        return texto, []

    faltando = []
    for campo in ESQUEMA:
        secao = bruto.get(campo.secao, {}) if campo.secao else bruto
        if isinstance(secao, dict) and campo.chave not in secao:
            faltando.append(campo)
    if not faltando:
        return texto, []

    linhas = texto.splitlines()
    for campo in faltando:
        bloco = _bloco_do_modelo(campo)
        cabecalhos = [i for i, l in enumerate(linhas) if re.match(r"^\s*\[", l)]
        if campo.secao is None:
            fim = cabecalhos[0] if cabecalhos else len(linhas)
        else:
            achado = [i for i in cabecalhos
                      if re.match(rf"^\s*\[{campo.secao}\]\s*$", linhas[i])]
            if not achado:
                # secao inteira ausente: vai para o fim, com o cabecalho
                if linhas and linhas[-1].strip():
                    linhas.append("")
                linhas += [f"[{campo.secao}]"] + bloco
                continue
            depois = [i for i in cabecalhos if i > achado[0]]
            fim = depois[0] if depois else len(linhas)
        # antes das linhas em branco que separam da proxima secao
        while fim > 0 and not linhas[fim - 1].strip():
            fim -= 1
        linhas[fim:fim] = bloco
    novo = "\n".join(linhas) + ("\n" if texto.endswith("\n") or not texto else "")
    return novo, [c.rotulo for c in faltando]


# --- carga e gravacao ------------------------------------------------------

def _gravar_atomico(caminho, texto):
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tmp = caminho.with_name(caminho.name + '.tmp')
    with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
        f.write(texto)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, caminho)


def _migrar_legado(legado):
    """Valores do window_config.json antigo (chaves em ingles), se validos."""
    config = _padrao_usuario()
    try:
        bruto = json.loads(Path(legado).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return config, {}
    if not isinstance(bruto, dict):
        return config, {}
    for campo in ESQUEMA:
        try:
            valor = _ler(bruto, campo.interno)
        except (KeyError, TypeError):
            continue
        if campo.validar(valor) is None:
            _escrever(config, campo.interno, valor)
    estado = {k: bruto[k] for k in ('geometry', 'editor') if k in bruto}
    return config, estado


def _carregar_estado(caminho):
    estado = json.loads(json.dumps(ESTADO_PADRAO))
    try:
        bruto = json.loads(Path(caminho).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return estado
    if isinstance(bruto, dict):
        if isinstance(bruto.get('geometry'), str):
            estado['geometry'] = bruto['geometry']
        if isinstance(bruto.get('editor'), dict):
            estado['editor'].update(bruto['editor'])
        if isinstance(bruto.get('recentes'), list):
            estado['recentes'] = [i for i in bruto['recentes'] if isinstance(i, str)][:10]
    return estado


def carregar_config(caminho=None, caminho_estado=None, caminho_legado=None):
    """(config, erros). Nunca levanta: sem config boa, usa os padroes.

    - TOML ausente: e criado - com os valores do window_config.json antigo, se
      ele existir (o antigo nao e apagado).
    - TOML invalido: padroes em memoria, arquivo INTOCADO, e os erros voltam
      para o app avisar. Sobrescrever apagaria o que o usuario escreveu.
    """
    caminho = Path(caminho or arquivo_config())
    caminho_estado = Path(caminho_estado or arquivo_estado())
    caminho_legado = Path(caminho_legado or arquivo_config_legado())

    erros = []
    if not caminho.exists():
        usuario, estado_legado = _migrar_legado(caminho_legado)
        try:
            _gravar_atomico(caminho, modelo_toml(usuario))
        except OSError as e:
            erros.append(f"não foi possível criar {caminho.name}: {e}")
        if estado_legado and not caminho_estado.exists():
            salvar_estado({**_padrao_completo(), **estado_legado},
                          estado_legado.get('geometry', ESTADO_PADRAO['geometry']),
                          caminho_estado)
    else:
        try:
            usuario, erros = validar_texto(caminho.read_text(encoding='utf-8'))
        except OSError as e:
            usuario, erros = None, [f"não foi possível ler {caminho.name}: {e}"]
        if usuario is None:
            usuario = _padrao_usuario()

    config = usuario
    config.update(_carregar_estado(caminho_estado))
    return config, erros


def ler_texto_config(caminho=None):
    """Texto cru do TOML para o editor; o modelo padrao se o arquivo sumiu."""
    try:
        return Path(caminho or arquivo_config()).read_text(encoding='utf-8')
    except OSError:
        return modelo_toml()


def salvar_texto_config(texto, caminho=None):
    """Grava EXATAMENTE o texto editado. Quem chama ja validou."""
    _gravar_atomico(caminho or arquivo_config(), texto)


def salvar_estado(config, geometria, caminho=None):
    """Grava so o estado do app. Nunca toca o TOML do usuario."""
    try:
        estado = {'geometry': geometria, 'editor': dict(config.get('editor', {})),
                  'recentes': list(config.get('recentes', []))[:10]}
        _gravar_atomico(caminho or arquivo_estado(),
                        json.dumps(estado, indent=4, ensure_ascii=False))
    except (OSError, TypeError, ValueError) as e:
        print(f"Erro ao salvar o estado da janela: {e}")


def aplicar_no_config(config, usuario):
    """Copia os valores do usuario para o config vivo, sem tocar o estado.

    Devolve o conjunto de secoes internas que mudaram ('theme', 'fonts', ...).
    """
    mudou = set()
    for campo in ESQUEMA:
        novo = _ler(usuario, campo.interno)
        if _ler(config, campo.interno) != novo:
            mudou.add(campo.interno[0])
            _escrever(config, campo.interno, novo)
    return mudou
