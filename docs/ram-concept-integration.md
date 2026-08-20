# RAM Concept Integration & Exporter Architecture

## 1. Overview
Bentley Systems RAM Concept is the premier software for elevated concrete floor slab and foundation design. This document outlines the technical mechanisms used to transfer extracted ETABS floor models into RAM Concept.

## 2. RAM Concept File Format & Integration Technical Research

### 2.1 Native RAM Concept Files (`.CPT`)
- **Format**: RAM Concept binary file container (internal SQLite database format with custom table structures).
- **Direct Creation Constraint**: Modifying `.CPT` binary database tables directly without Bentley's proprietary C++ framework can cause model corruption.
- **Native Automation Approach**: Automated `.CPT` creation is performed via RAM Concept COM Automation or CAD DXF Layer Ingestion.

### 2.2 Standard DXF Layer Exchange Format (Universal Standard)
RAM Concept supports automated drawing import from DXF files with predefined structural layer names:

| RAM Concept Layer | DXF Entity Type | Description |
| :--- | :--- | :--- |
| `SLAB_OUTLINE` | Closed Polyline | Floor slab boundary polygon |
| `OPENINGS` | Closed Polyline | Void / slab opening boundary |
| `COLUMNS_BELOW` | Point / Circle / Polyline | Lower story column support location & dimensions |
| `COLUMNS_ABOVE` | Point / Circle / Polyline | Upper story column reaction location |
| `WALLS_BELOW` | Line / Polyline | Lower story wall line support |
| `WALLS_ABOVE` | Line / Polyline | Upper story wall line support |
| `BEAMS` | Line / Polyline | Beam centerlines and section widths |
| `SURFACE_LOADS` | Polyline + Text | Area load patches with magnitude |
| `POINT_LOADS` | Point + Text | Concentrated point loads and moments |

### 2.3 RAM Concept COM Automation Interface
- **ProgIDs**:
  - `RAMConcept.Application`
  - `RAMConcept.Application.1`
  - `Bentley.RAM.Concept`
- **Capabilities**:
  - `NewDocument()`
  - `ImportDXF(dxfPath, mappingSettings)`
  - `SaveAs(cptFilePath)`
- **Windows Worker Pipeline**:
  - The web application generates a Python script (`export_ram_macro.py`) that uses `comtypes` / `win32com` to launch RAM Concept on Windows worker nodes, import the generated DXF, apply slab thickness/materials, and save a native `.CPT` file.

### 2.4 Intermediate Structural Model (ISM) JSON Format
- Structured JSON representation of isolated floor geometry and loadings.
- Enables direct integration with Bentley iTwin / ISM services or custom client-side Python automation scripts.

---

## 3. Floor Extraction Modes

1. **Mode A — Slab Only**:
   - Slab outlines, openings, slab properties, surface loads.
2. **Mode B — Slab + Supporting Elements**:
   - Mode A + Beams on floor level + Supporting Columns (above & below) + Supporting Walls (above & below) + Support Restraints.
3. **Mode C — Complete Structural Model**:
   - Mode B + Superimposed loads, equivalent column stiffness boundary conditions, live load patterns, and full load combination definitions for finite element analysis in RAM Concept.

---

## 4. Coordinate Transformation Pipeline
```text
ETABS Global Coordinates (X, Y, Z_story)
             ↓
Normalize Elevation (Set Z = 0.0 on Floor Plane)
             ↓
Apply Project Base Point Offset
             ↓
DXF Polyline Entity Generation
             ↓
RAM Concept Native Coordinate Import
```
