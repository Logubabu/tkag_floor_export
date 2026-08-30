# -*- mode: python ; coding: utf-8 -*-

import os
import sys

block_cipher = None

project_dir = os.path.dirname(os.path.abspath(SPEC))

datas = [
    (os.path.join(project_dir, 'backend'), 'backend'),
    (os.path.join(project_dir, 'gui'), 'gui'),
]

hiddenimports = [
    'PySide6',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'shapely',
    'shapely.geometry',
    'pandas',
    'pydantic',
    'win32com',
    'win32com.client',
    'comtypes',
    'sqlite3',
    'zlib',
    'backend.app.etabs.e2k_parser',
    'backend.app.etabs.edb_parser',
    'backend.app.floor_extractor.extractor',
    'backend.app.models.intermediate',
    'backend.app.ram_concept.exporter',
    'backend.app.ram_concept.ram_detector',
    'gui.app_gui',
    'gui.model_viewer',
]

excludes = [
    'tkinter', 'Tkinter', 'turtle', 'matplotlib', 'scipy', 'IPython',
    'shapely.tests', 'pandas.tests', 'pytest'
]

a = Analysis(
    ['main_app.py'],
    pathex=[project_dir, os.path.join(project_dir, 'backend')],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
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
    name='ETABS_to_RAM_Concept_Exporter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # Set upx=False for ultra-fast build speed
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
