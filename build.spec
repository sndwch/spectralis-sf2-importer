# -*- mode: python ; coding: utf-8 -*-
import sys

a = Analysis(
    ['entry.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['sf2utils', 'sf2utils.sf2parse', 'sf2utils.sample',
                   'sf2utils.preset', 'sf2utils.instrument', 'sf2utils.bag',
                   'sf2utils.generator', 'sf2utils.modulator', 'sf2utils.riffparser'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SF2Converter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=(sys.platform == 'darwin'),
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='SF2Converter.app',
        icon=None,
        bundle_identifier='com.spectralis2tools.sf2converter',
    )
