# -*- mode: python ; coding: utf-8 -*-
# Debug build: same app but WITH a console window, so running Xubair-debug.exe from cmd
# prints the full error/traceback if anything goes wrong.
from PyInstaller.utils.hooks import collect_all

block_cipher = None

datas = [('Sprites', 'Sprites')]
binaries = []
hiddenimports = ['PIL._tkinter_finder', 'pystray._win32', 'psutil']
for pkg in ('tkinterdnd2',):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    ['run_xubair.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='Xubair-debug',
    debug=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,        # shows a console with errors
    icon=None,
)
