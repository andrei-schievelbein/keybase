"""Resolucao de caminhos: diretorio base, diretorio de dados e recursos embutidos.

Isola todo o conhecimento sobre PyInstaller (sys.frozen / sys._MEIPASS) num
lugar so. Regra critica: sys._MEIPASS e o diretorio temporario de extracao,
apagado a cada execucao - serve para recursos somente leitura (icone), JAMAIS
para dados do usuario.
"""

import os
import sys
from pathlib import Path

APP_NAME = "KeyBase"


def esta_congelado():
    """True quando rodando a partir do executavel gerado pelo PyInstaller."""
    return getattr(sys, 'frozen', False)


def base_dir():
    """Diretorio do executavel (congelado) ou da raiz do projeto (script)."""
    if esta_congelado():
        return Path(sys.executable).parent
    # paths.py fica em keybase/, entao a raiz do projeto e o pai
    return Path(__file__).resolve().parent.parent


def recurso(nome):
    """Caminho de um recurso embutido no executavel. SOMENTE LEITURA.

    Quando congelado, o PyInstaller extrai os 'datas' para sys._MEIPASS.
    """
    if esta_congelado():
        return Path(getattr(sys, '_MEIPASS', base_dir())) / nome
    return base_dir() / nome


def _gravavel(diretorio):
    """Testa de fato se da para escrever no diretorio, criando um arquivo."""
    try:
        diretorio.mkdir(parents=True, exist_ok=True)
        teste = diretorio / '.write_test'
        teste.write_text('', encoding='utf-8')
        teste.unlink()
        return True
    except OSError:
        return False


def dir_dados():
    """Diretorio onde ficam os dados do usuario.

    Preferencia pelo diretorio do app (uso portatil, pen drive). Se ele nao for
    gravavel - caso classico do .exe instalado em C:\\Program Files - cai para o
    diretorio de dados do usuario, em vez de perder os saves silenciosamente.
    """
    base = base_dir()
    if _gravavel(base):
        return base

    if os.name == 'nt':
        raiz = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
        alternativo = raiz / APP_NAME
    else:
        alternativo = Path.home() / '.keybase'

    alternativo.mkdir(parents=True, exist_ok=True)
    return alternativo


def arquivo_dados():
    """Caminho do arquivo de dados da arvore."""
    return dir_dados() / 'keybase_data.json'


def arquivo_config():
    """Configuracao do usuario, editavel com C dentro do app."""
    return dir_dados() / 'keybase_config.toml'


def arquivo_estado():
    """Estado da janela (geometria, ultimo modo do editor), gravado pelo app."""
    return dir_dados() / 'keybase_estado.json'


def arquivo_config_legado():
    """O window_config.json de antes do TOML: so lido, para migrar os valores."""
    return dir_dados() / 'window_config.json'
