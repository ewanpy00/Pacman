# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the packaged Pac-Man build.
#
#   make package        # or:  pyinstaller pacman.spec
#
# Produces a single-file executable in dist/ that bundles config.json plus the
# whole game package and the assigned maze generator.

block_cipher = None

a = Analysis(
    ['scripts/launcher.py'],
    pathex=['.'],
    binaries=[],
    # Bundle the default config and the game source next to the executable.
    datas=[
        ('config.json', '.'),
        ('src', 'src'),
    ],
    # Imported lazily / by string, so name them explicitly.
    hiddenimports=['mazegenerator', 'pygame'],
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter', 'numpy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
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
    name='pacman',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=False,   # windowed app (no terminal)
)
