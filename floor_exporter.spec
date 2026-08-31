# -*- mode: python ; coding: utf-8 -*-

import os
import sys

block_cipher = None

project_dir = os.path.dirname(os.path.abspath(SPEC))

import sysconfig

site_packages = sysconfig.get_path('platlib')
pywin32_system32 = os.path.join(site_packages, 'pywin32_system32')

binaries = []
if os.path.exists(pywin32_system32):
    for f in os.listdir(pywin32_system32):
        if f.endswith('.dll'):
            binaries.append((os.path.join(pywin32_system32, f), '.'))

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
    'shapely.validation',
    'pandas',
    'pydantic',
    'win32com',
    'win32com.client',
    'win32com.client.gencache',
    'win32com.client.dynamic',
    'win32com.client.CLSIDToClassMap',
    'win32com.client.build',
    'win32com.client.makepy',
    'pythoncom',
    'pywintypes',
    'comtypes',
    'comtypes.client',
    'sqlite3',
    'zlib',
    'app.etabs.e2k_parser',
    'app.etabs.edb_parser',
    'app.etabs.com_adapter',
    'app.etabs.version_detector',
    'app.floor_extractor.extractor',
    'app.floor_extractor.tributary_engine',
    'app.geometry.processor',
    'app.models.intermediate',
    'app.ram_concept.exporter',
    'app.ram_concept.ram_detector',
    'app.ram_concept.com_adapter',
    'app.reports.report_generator',
    'app.validation.validator',
    'backend.app.etabs.e2k_parser',
    'backend.app.etabs.edb_parser',
    'backend.app.etabs.com_adapter',
    'backend.app.etabs.version_detector',
    'backend.app.floor_extractor.extractor',
    'backend.app.floor_extractor.tributary_engine',
    'backend.app.geometry.processor',
    'backend.app.models.intermediate',
    'backend.app.ram_concept.exporter',
    'backend.app.ram_concept.ram_detector',
    'backend.app.ram_concept.com_adapter',
    'backend.app.reports.report_generator',
    'backend.app.validation.validator',
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
    binaries=binaries,
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
