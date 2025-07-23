# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['dotnet_runtime_gui.py'],
    pathex=[],
    binaries=[],
    datas=[('winrar_base64.txt', '.'),
    ('forticlient_base64.txt', '.'),
    ('vnc_base64.txt', '.'),
    ('office_base64.txt', '.'),
    ('winrar_base64.png', '.'),
    ('forticlient_base64.png', '.'),
    ('chrome_icon.png', '.'),
    ('tightvnc_icon_resized.png', '.'),
    ('office_base64.png', '.'),
    ('yorglass.ico', '.')
    
    ],
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
    name='dotnet_runtime_gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    icon='yorglass.ico',
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
