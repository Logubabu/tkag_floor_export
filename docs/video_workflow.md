# ETABS → RAM Concept Engineering Workflow & Technical Specification

## Overview
This document details the step-by-step structural engineering workflow automated by the **ETABS RAM Concept Exporter** desktop application.

---

## Technical Workflow Pipeline

```text
  [ETABS Model (.EDB, .E2K, $ET, .ET)]
                 │
                 ▼
  1. Source & Mode Detection
     - Auto-detect live COM API (ETABS 20.x, 21.x+) or offline text parser ($ET / .E2K)
                 │
                 ▼
  2. Model Extraction & Data Normalization
     - Extract project info, units, stories, nodes, slabs, walls, columns, beams, openings, supports, materials, sections, and area loads
     - Transform into Normalized Internal Structural Model
                 │
                 ▼
  3. Interactive Story Selection
     - Display elevation hierarchy (Roof, Floor 10, Floor 9, ..., Base)
     - Allow Single, Multi, All, Invert floor selection
     - Apply spatial bounding rules for vertical elements (columns/walls above/below floor)
                 │
                 ▼
  4. 2D Floor Plan & 3D Interactive Visualization
     - 2D Canvas viewer with layer visibility toggles (Slabs, Beams, Columns, Walls, Openings, Supports)
     - Interactive element inspection (object ID, section, material, thickness, coordinates)
     - 3D Viewport canvas with story elevation filtering
                 │
                 ▼
  5. 20-Point Validation Engine
     - Self-intersecting polygon checks, zero-area slab check, zero-length beam check
     - Missing section/material check, duplicate node/element removal
     - Polygon orientation sanitization: auto-fix clockwise loops to Counter-Clockwise (CCW)
                 │
                 ▼
  6. Structural Mapping & Conversion
     - Map ETABS slabs → RAM Concept Slab Areas & Concrete Properties
     - Map ETABS walls → RAM Concept Walls (Above/Below)
     - Map ETABS columns → RAM Concept Columns (Above/Below)
     - Map ETABS beams → RAM Concept Slab Strips / Drop Panels / Beams
     - Map ETABS openings → RAM Concept Openings
     - Map ETABS surface loads → RAM Concept Load Cases & Load Combos
                 │
                 ▼
  7. RAM Concept Output Generation
     - Native Binary .CPT (via Bentley ram_concept Python API + SQLite geometry layout)
     - CAD Structural Exchange .CPF
     - CAD Drawing Exchange .DXF (Layered: SLAB_OUTLINE, BEAMS, COLUMNS_BELOW, WALLS_BELOW, OPENINGS)
                 │
                 ▼
  8. Post-Export Verification & Conversion Report
     - Verify generated output file presence, size, object count parity
     - Generate HTML, JSON, and CSV conversion audit reports
```

---

## Data Transfer Rules

| ETABS Entity | RAM Concept Target Entity | Geometry Handling | Property Mapping |
| :--- | :--- | :--- | :--- |
| **Slab/Area** | Slab Area Plan | Polygon Vertices (CCW) | Thickness, Concrete $f'_c$, Rebar $f_y$ |
| **Wall** | Wall Below / Above Plan | Line / Polygon Envelope | Thickness, Height, Offset |
| **Column** | Column Below / Above Plan | Point + Cross Section | Dimensions ($b \times h$), Rigid Zones |
| **Beam** | Beam / Slab Strip Plan | Centerline + Profile | Width, Depth, Eccentricity |
| **Opening** | Slab Opening Plan | Polygon Hole Vertices | Cuts underlying slab area |
| **Area Load** | Uniform Surface Load Plan | Polygon Bounds | Pattern (Dead, Live, Super Dead) |
| **Support** | Rigid Point/Line Support | Point/Line Restraint | Fixed / Pinned Degrees of Freedom |

---

## Error Handling & Data Integrity
- **No Data Loss**: Every extracted object is tracked in the object lifecycle table. Objects requiring manual intervention are flagged as `MANUAL_REVIEW_REQUIRED`.
- **Polygon Sanitization**: Non-planar or self-intersecting slab polygons are repaired using Shapely buffer polygon decomposition.
- **Unit Scaling**: Explicit unit transformation matrices prevent scale mismatches between ETABS (e.g. `kN-m`) and RAM Concept (e.g. `kip-ft` or `N-mm`).
