# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_all

datas = [('frontend/dist', 'static'), ('backend/app', 'app')]
binaries = []
hiddenimports = [
    'win32com',
    'win32com.client',
    'pythoncom',
    'win32api',
    'pydantic',
    'starlette',
    'uvicorn.protocols.http.h11_impl',
    'uvicorn.loops.auto',
    'uvicorn.lifespan.on',
]

packages_to_collect = [
    'fastapi',
    'uvicorn',
    'shapely',
    'comtypes',
    'win32com',
    'pywin32',
    'pydantic',
    'starlette',
]

for pkg in packages_to_collect:
    try:
        tmp_ret = collect_all(pkg)
        datas += tmp_ret[0]
        binaries += tmp_ret[1]
        hiddenimports += tmp_ret[2]
    except Exception:
        pass

a = Analysis(
    ['desktop_app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# 1. Folder Distribution Output
exe_folder = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ETABS_RAMConcept_Floor_Exporter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe_folder,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ETABS_RAMConcept_Floor_Exporter_Folder',
)

# 2. Standalone Single File (.exe) Output
exe_singlefile = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ETABS_RAMConcept_Floor_Exporter_SingleFile',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

