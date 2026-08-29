# ETABS to RAM Concept Floor Exporter Platform

A standalone Windows desktop application for structural engineers to ingest ETABS 3D building models (`.$et`, `.e2k`, `.edb`), extract floor structural geometry, auto-detect Bentley RAM Concept installations, and export native RAM Concept model files (`.cpt`), DXF exchange drawings (`.dxf`), and Python COM macro scripts (`.py`).

---

## 🏛️ Key Features

- **ETABS Model Support**: Ingests ETABS text exports (`.$et`, `.e2k`) and binary database files (`.edb`).
- **Floor Geometry Extraction**: Extracts story elevations, slab boundaries, openings, slab thicknesses, floor beams, supporting columns (above & below), shear walls, materials, and load patterns.
- **Bentley RAM Concept Auto-Detection**: Automatically scans standard installation directories (`C:\Program Files\Bentley\Engineering\RAM Concept\...`), Windows Registry, and registered COM servers to detect RAM Concept versions (2023 / 2024 / 2025).
- **Native `.CPT` Binary Model Generation**: Directly invokes Bentley's `ram_concept` Python API / COM automation to generate 100% genuine binary `.cpt` model files.
- **Independent Import & Export Paths**: Pick any ETABS model file location and choose any destination directory for your exported files every time you click Export.
- **Pure Python Desktop GUI**: Built using **PySide6 (Qt for Python)** for a modern, responsive, non-freezing dark desktop interface.

---

## 💻 How to Run the Application

### Method 1: Run the Standalone Desktop Executable (`.exe`)

Double-click the generated `.exe` file or run it from Command Prompt / PowerShell:

```cmd
# Command Prompt / PowerShell:
.\dist\ETABS_to_RAM_Concept_Exporter.exe
```

---

### Method 2: Run from Python Source Code

#### 1. Install Dependencies
```cmd
pip install PySide6 shapely pandas pydantic pywin32 comtypes etabs_api
```

#### 2. Launch the Desktop Application
```cmd
python main_app.py
```

---

## 📖 Step-by-Step UI Usage Guide

1. **Select ETABS Model File**:
   - Click **Browse ETABS File...** and select your ETABS file (`.$et`, `.e2k`, or `.edb`).
2. **Parse Model Data**:
   - Click **Parse & Extract**. The application parses the building structure and populates the story levels list.
3. **Select Floors to Export**:
   - Use the table checkboxes to select the individual floor(s) or click **Select All**.
4. **Check RAM Concept Status**:
   - The top banner displays detected RAM Concept installation path and status (e.g. `✓ Detected RAM Concept 2024`).
5. **Export Files**:
   - Click **EXPORT SELECTED FLOORS TO RAM CONCEPT (.CPT)**.
   - When prompted by the folder picker dialog, select your desired **Destination Folder**.
   - Output files (`*_RAMConcept_Model.cpt`, `*_RAMConcept_Exchange.dxf`, `*_RAMConcept_Automation.py`, `*_IntermediateModel.json`) will be saved directly into your chosen destination folder.

---

## 🛠️ How to Build the Executable (`.exe`) Procedure

To compile the application into a single standalone Windows executable (`ETABS_to_RAM_Concept_Exporter.exe`) using PyInstaller:

### 1. Install PyInstaller
```cmd
pip install pyinstaller
```

### 2. Run PyInstaller with Spec File
```cmd
pyinstaller floor_exporter.spec --noconfirm
```

### 3. Executable Output Location
Upon completion, PyInstaller generates the standalone executable at:
```text
d:\Projects\TKAG\floor_export_exe\dist\ETABS_to_RAM_Concept_Exporter.exe
```

---

## 📁 Directory Structure

```text
floor_export_exe/
├── backend/
│   └── app/
│       ├── etabs/        # E2K & EDB parsers, COM adapter
│       ├── floor_extractor/ # Floor extraction engine
│       ├── geometry/     # Shapely geometry processing & coordinate normalization
│       ├── models/       # Intermediate Structural Model schemas
│       ├── ram_concept/  # RAM Concept exporter & auto-detector module
│       └── validation/   # Structural rule validator
│
├── gui/
│   └── app_gui.py        # Modern PySide6 Qt GUI main window & threads
│
├── dist/
│   └── ETABS_to_RAM_Concept_Exporter.exe  # Standalone Windows Executable
│
├── main_app.py           # Application entry point script
├── floor_exporter.spec   # PyInstaller build specification file
├── sample_models/        # Sample ETABS test models
└── README.md             # Application Documentation & User Guide
```
