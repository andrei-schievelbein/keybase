# -*- mode: python ; coding: utf-8 -*-
import os


a = Analysis(
    ['keybase.pyw'],
    pathex=[SPECPATH],  # resolve o pacote keybase/ ao lado do entrypoint
    binaries=[],
    datas=[(os.path.join(SPECPATH, 'keybase.ico'), '.')],  # Incluir o ícone no executável
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    upx=True,
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
