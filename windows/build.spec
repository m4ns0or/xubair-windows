# -*- mode: python ; coding: utf-8 -*-
block_cipher = None

a = Analysis(
    ['xubair_win.py'],
    pathex=[],
    binaries=[],
    datas=[('Sprites', 'Sprites')],
    hiddenimports=['PIL._tkinter_finder'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Xubair',
    debug=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,       # no terminal window
    icon=None,           # supply a .ico here if you have one
)
