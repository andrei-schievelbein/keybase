# -*- mode: python ; coding: utf-8 -*-
import os

from PyInstaller.utils.hooks import collect_submodules


a = Analysis(
    ['keybase.pyw'],
    pathex=[SPECPATH],  # resolve o pacote keybase/ ao lado do entrypoint
    binaries=[],
    datas=[(os.path.join(SPECPATH, 'keybase.ico'), '.')],  # Incluir o ícone no executável
    # Pygments carrega lexers por nome em runtime e o markdown carrega
    # extensoes por entry point: nenhum dos dois e visivel a analise estatica.
    hiddenimports=(
        collect_submodules('pygments.lexers')
        + collect_submodules('markdown.extensions')
        + collect_submodules('pymdownx')
    ),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # sem isto o PyInstaller detecta o Tcl/Tk da instalacao e arrasta ~10 MB
        'tkinter', '_tkinter', 'customtkinter', 'PIL', 'darkdetect',
        # o app usa QTextBrowser, nao QWebEngine
        'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
        'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.Qt3DCore',
        'PySide6.QtMultimedia', 'PySide6.QtCharts',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='keybase',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,   # UPX corrompe DLLs do Qt no Windows
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[os.path.join(SPECPATH, 'keybase.ico')],
)
