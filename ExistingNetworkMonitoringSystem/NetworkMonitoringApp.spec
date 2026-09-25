# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all


model_datas = []
model_binaries = []
model_hidden_imports = []
for package in ("sklearn", "xgboost", "torch"):
    package_datas, package_binaries, package_hidden_imports = collect_all(package)
    model_datas += package_datas
    model_binaries += package_binaries
    model_hidden_imports += package_hidden_imports


a = Analysis(
    ['desktop_app.py'],
    pathex=[],
    binaries=model_binaries,
    datas=[('templates', 'templates'), ('static', 'static')] + model_datas,
    hiddenimports=model_hidden_imports,
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
    name='NetworkMonitoringApp',
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
)
