# ETABS to RAM Concept Floor Exporter Platform

A production-ready Windows desktop application for structural engineers to convert ETABS 3D building models (`.EDB`, `.ET`, `$ET`, `.E2K`) into Bentley RAM Concept model files (`.cpt`), CAD Structural Exchange files (`.cpf`), and DXF exchange drawings (`.dxf`).

---

## 🏛️ Architecture & Processing Pipeline

```text
ETABS (.EDB, .ET, $ET, .E2K)
       │
       ├──► Mode 1: Live ETABS API Adapter (COM Interface for installed ETABS)
       └──► Mode 2: Offline File Parser Engine (.E2K, $ET text parser)
       │
       ▼
Normalized Internal Structural Model
(Stories, Slabs, Beams, Columns, Walls, Openings, Supports, Loads, Materials, Sections)
       │
       ▼
Validation & Rule Engine
(Checks geometry, duplicate elements, connectivity, unit consistency)
       │
       ▼
Interactive Floor Selection & 2D/3D Canvas Viewer
       │
       ▼
RAM Concept Mapping & Export Engine
       ├──► Native Binary .CPT (via Bentley ram_concept Python API + Mesh Generation)
       ├──► CAD Exchange .CPF (Full DXF Structural Exchange entities)
       └──► CAD Exchange .DXF (Drawing exchange layers)
```

---

## 🏛️ Key Features & Capability Matrix

- **Processing Modes**:
  - **ETABS LIVE Mode**: Connects via COM API (`CSI.ETABS.API.ETABSObject`) to active running ETABS instances or installed versions (20.x, 21.x+).
  - **OFFLINE PARSER Mode**: Local text parser for `$ET` and `.E2K` files requiring no local ETABS installation.
- **Drag & Drop UI**: Drop `.EDB`, `.ET`, `$ET`, or `.E2K` files directly onto the desktop interface.
- **Story Selection**: Select single or multiple stories for batch export.
- **2D/3D Model View**: Interactive 2D floor plan view with layer controls (Slabs, Beams, Columns, Walls, Openings) and 3D viewport canvas.
- **Bentley RAM Concept API Auto-Detection**: Auto-detects RAM Concept 2023, 2024, and 2025 installations from system paths and registry.
- **Validated RAM Concept Export**: Generates `.cpt` binary models with automatic Counter-Clockwise (CCW) polygon sanitization and finite element mesh generation, alongside CAD exchange `.cpf` files.

---

## 💻 How to Run the Desktop Application

### Method 1: Standalone Desktop Executable (`.exe`)
Run the compiled 64-bit Windows executable directly from PowerShell or Command Prompt:

```cmd
.\dist\ETABS_to_RAM_Concept_Exporter.exe
```

### Method 2: Launch from Python Source Code

#### 1. Install Dependencies
```cmd
pip install PySide6 shapely pandas pydantic pywin32 comtypes etabs_api
```

#### 2. Launch App
```cmd
python main_app.py
```

---

## 👁️ How to View Exported Files in Bentley RAM Concept

### Option 1: Opening the Native Model File (`.CPT`)
1. Open **Bentley RAM Concept** and select **File → Open...**.
2. Choose your exported `.cpt` file (e.g. `Roof_RAMConcept_Model.cpt`).
3. In the left-hand **Layer Tree / Layer List**:
   - Double-click **Structure Layer → Slab Area Plan** (or **Structure Plan**).
4. All structural elements (**Slabs**, **Beams**, **Columns**, **Walls**, and **Openings**) will immediately render in full 3D layout view.

### Option 2: Importing the CAD Structural File (`.DXF` / `.CPF`)
1. Open **Bentley RAM Concept**.
2. Go to **File → Import → CAD File...** (or Drawing File).
3. Select the exported `.dxf` or `.cpf` file (`Roof_RAMConcept_Exchange.dxf`).
4. All structural drawing layers (`SLAB_OUTLINE`, `BEAMS`, `COLUMNS_BELOW`, `WALLS_BELOW`, `OPENINGS`) will import onto your active CAD Drawing plan.

---

## 🛠️ Executable Build Procedure

To compile the application into a single standalone Windows executable (`ETABS_to_RAM_Concept_Exporter.exe`) using PyInstaller:

```cmd
# 1. Install PyInstaller
pip install pyinstaller

# 2. Compile executable using spec file
pyinstaller floor_exporter.spec --noconfirm
```

Output binary:
`d:\Projects\TKAG\floor_export_exe\dist\ETABS_to_RAM_Concept_Exporter.exe`

---

## 📁 Project Structure

```text
floor_export_exe/
├── backend/
│   └── app/
│       ├── etabs/        # Live COM API & E2K/ET offline parsers
│       ├── floor_extractor/ # Multi-story extraction engine
│       ├── geometry/     # Shapely polygon & coordinate scaling
│       ├── models/       # Normalized Internal Structural Model schemas
│       ├── ram_concept/  # RAM Concept exporter & Bentley API auto-detector
│       └── validation/   # Structural rule validation engine
│
├── gui/
│   ├── app_gui.py        # PySide6 Qt GUI main window & threads
│   └── model_viewer.py   # 2D/3D Model viewer canvas
│
├── dist/
│   └── ETABS_to_RAM_Concept_Exporter.exe  # Standalone Windows Executable
│
├── main_app.py           # Application entry point
├── floor_exporter.spec   # PyInstaller spec configuration
└── README.md             # Documentation & Architecture guide
```
