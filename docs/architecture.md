# Architecture & System Design

## 1. System Architecture Diagram

```text
 ┌────────────────────────────────────────────────────────┐
 │                   React + Vite Client                  │
 │                                                        │
 │  ┌─────────────────┐ ┌───────────────┐ ┌────────────┐  │
 │  │ 3D R3F Viewport │ │ Story Tree UI │ │ Inspectors │  │
 │  └─────────────────┘ └───────────────┘ └────────────┘  │
 └───────────────────────────┬────────────────────────────┘
                             │ REST API / Axios
                             ▼
 ┌────────────────────────────────────────────────────────┐
 │                     FastAPI Backend                    │
 │                                                        │
 │  ┌─────────────────┐ ┌───────────────┐ ┌────────────┐  │
 │  │ E2K / COM Parser│ │Geometry Engine│ │ Validator  │  │
 │  └────────┬────────┘ └───────┬───────┘ └─────┬──────┘  │
 │           │                  │               │         │
 │           ▼                  ▼               ▼         │
 │            Intermediate Structural Model               │
 │                          │                             │
 │                          ▼                             │
 │                Floor Extractor (A/B/C)                 │
 │                          │                             │
 │                          ▼                             │
 │                 RAM Concept Exporter                   │
 └──────────────────────────┬─────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
 ┌────────────────────────┐  ┌────────────────────────┐
 │ DXF CAD Layer Package  │  │ Windows COM Worker     │
 │ & Intermediate JSON    │  │ (RAM Concept .CPT)     │
 └────────────────────────┘  └────────────────────────┘
```

## 2. Core Modules

### 2.1 Backend Modules (`backend/app/`)
- `models/intermediate.py`: Pydantic V2 domain models for `BuildingModel`, `Story`, `Node`, `Frame`, `Slab`, `Wall`, `Material`, `Section`, `Load`, `ValidationResult`.
- `etabs/e2k_parser.py`: Fast string tokenizing parser for ETABS `.e2k` text export files.
- `etabs/com_adapter.py`: Windows COM wrapper for direct live ETABS instance communication.
- `geometry/processor.py`: Shapely computational geometry engine for polygon validity, ring orientation, opening containment, coordinate normalization, and unit conversion.
- `floor_extractor/extractor.py`: Story extraction algorithm filtering structural members, detecting column/wall supports above & below story elevation, and assembling isolated floor models.
- `validation/validator.py`: Structural rule engine catching geometric self-intersections, missing properties, orphaned nodes, and unsupported loads.
- `ram_concept/exporter.py`: DXF file writer, Python COM script generator, and JSON exporter for RAM Concept.
- `workers/job_manager.py`: Async job queue for background model processing and progress reporting.
- `api/routes.py`: REST API endpoints for projects, models, floors, validation, exports, and background jobs.

### 2.2 Frontend Modules (`frontend/src/`)
- `viewer/StructuralViewer.tsx`: Three.js / React Three Fiber interactive 3D view with camera controls, orbit presets, element raycasting, and visual layer toggles.
- `components/FloorTree.tsx`: Building hierarchy list with story elevation, master story indicator, and member counts.
- `components/PropertyPanel.tsx`: Detailed element inspector showing geometry, section dimensions, thickness, and materials.
- `components/ValidationCard.tsx`: Formatted report showing errors, warnings, and remediation tips.
- `components/ExportModal.tsx`: File download manager for DXF CAD layers, Python macro scripts, and JSON schema files.
