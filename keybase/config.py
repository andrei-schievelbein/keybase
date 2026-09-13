"""Configuracao da janela e preferencias do usuario (window_config.json).

Preservado quase intacto da versao anterior - so passou a usar paths.py e a
nao depender de variavel global.
"""

import json

import customtkinter as ctk

from .paths import arquivo_config

DEFAULT_CONFIG = {
    'geometry': '800x600',
    'theme': 'dark',
    '_instrucoes': {
        'tema': "Opções disponíveis: 'dark' (escuro) ou 'light' (claro)",
        'fontes': "Recomendado usar fontes monoespaçadas: 'Consolas', 'Courier New', 'Roboto Mono', 'Fira Code'",
        'tamanhos': "Tamanhos são definidos em pixels",
    },
    'fonts': {
        'input_size': 12,
        'output_size': 14,
        'help_size': 12,
        'family': 'Consolas',
        'fallback': 'Courier New',
    },
    'interface': {
        'help_area_height': 60,
    },
}


def carregar_config():
    """Le a config salva, mesclando com os padroes para garantir as chaves."""
    caminho = arquivo_config()
    if not caminho.exists():
        return _copia_profunda(DEFAULT_CONFIG)

    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except (json.JSONDecodeError, OSError):
        return _copia_profunda(DEFAULT_CONFIG)

    for chave, valor in DEFAULT_CONFIG.items():
        if chave not in config:
            config[chave] = _copia_profunda(valor)
        elif isinstance(valor, dict) and isinstance(config[chave], dict):
            for subchave, subvalor in valor.items():
                config[chave].setdefault(subchave, subvalor)
    return config


def salvar_config(janela, config_atual):
    """Grava a config, com as instrucoes no topo para quem editar a mao."""
    try:
        config = dict(config_atual)
        config['geometry'] = janela.geometry()

        ordenado = {
            '_instrucoes': config.pop('_instrucoes', DEFAULT_CONFIG['_instrucoes'])
        }
        ordenado.update(config)

        with open(arquivo_config(), 'w', encoding='utf-8') as f:
            json.dump(ordenado, f, indent=4, ensure_ascii=False)
    except OSError as e:
        print(f"Erro ao salvar config: {e}")


def aplicar_tema(tema):
    ctk.set_appearance_mode(tema)


def _copia_profunda(valor):
    if isinstance(valor, dict):
        return {k: _copia_profunda(v) for k, v in valor.items()}
    return valor
