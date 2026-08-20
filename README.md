# ETABS to RAM Concept Floor Extraction Platform

A professional web application for structural engineers to take complete ETABS 3D building models, isolate individual floor slab systems, visualize and inspect structural elements in interactive 3D (React Three Fiber), validate geometry using Shapely, and export RAM Concept-ready packages.

---

## 🏛️ Key Features

- **ETABS Ingestion**: Ingests ETABS `.E2K` / `.S2K` text export files containing complete building geometry, materials, sections, and loadings, with live COM API bridge on Windows.
- **Smart Floor Extraction Engine**:
  - **Mode A (Slab Only)**: Slab boundaries, openings, thickness, area properties, and slab loads.
  - **Mode B (Slab + Supporting Elements)**: Slabs, openings, floor beams, supporting columns (above & below), and shear walls.
  - **Mode C (Complete Floor Model)**: Slabs, supports, equivalent spring boundary conditions, live load patterns, and point/line loads.
- **Interactive 3D WebGL Viewer**:
  - Rendered with Three.js & React Three Fiber.
  - Controls for Orbit, Pan, Zoom, Perspective, Orthographic, Top, Front, and Side camera views.
  - Raycasting element selection with detailed property inspector panel.
  - Layer toggles (Slabs, Beams, Columns, Walls, Nodes, Loads).
- **Engineering Validation Engine**:
  - Checks for degenerate geometries, self-intersecting polygons, zero thickness, missing material definitions, and orphan supports.
  - Returns actionable engineering remediation tips.
- **RAM Concept Exporter**:
  - **DXF CAD Exchange**: Standard layer layout (`SLAB_OUTLINE`, `OPENINGS`, `COLUMNS_ABOVE`, `COLUMNS_BELOW`, `BEAMS`).
  - **RAM Concept COM Macro Script**: Automated Python script to launch Bentley RAM Concept on Windows worker nodes.
  - **Intermediate Structural Model (ISM) JSON**: Open ISO structural schema.

---

## 📁 Directory Structure

```text
etabs-ram-converter/
├── frontend/             # React + TypeScript + Vite + Tailwind CSS + Three.js / R3F
│   ├── src/
│   │   ├── components/   # UI Header, FloorTree, PropertyPanel, Modals, DropZone
│   │   ├── viewer/       # StructuralViewer (React Three Fiber WebGL canvas)
│   │   ├── store/        # Zustand state store
│   │   ├── services/     # API fetch client
│   │   └── types/        # TypeScript interface definitions
│   └── package.json
│
├── backend/              # FastAPI + Pydantic + Shapely + NumPy
│   ├── app/
│   │   ├── api/          # REST API endpoints
│   │   ├── models/       # Intermediate Structural Model schemas
│   │   ├── etabs/        # E2K text parser & Windows COM adapter
│   │   ├── geometry/     # Shapely polygon validator & unit converters
│   │   ├── floor_extractor/ # Floor Extraction Engine (Modes A, B, C)
│   │   ├── validation/   # Structural rule validator
│   │   ├── ram_concept/  # RAM Concept DXF & COM script exporter
│   │   └── workers/      # Async background job manager
│   ├── tests/            # Pytest suite
│   └── requirements.txt
│
├── docs/                 # Engineering Architecture & API Research Docs
│   ├── etabs-integration.md
│   ├── ram-concept-integration.md
│   ├── architecture.md
│   └── supported-features.md
│
├── sample_models/        # Sample ETABS .e2k test files
├── docker/               # Backend & Frontend Dockerfiles
├── docker-compose.yml
└── README.md
```

---

## 🚀 Quick Start (Local Development)

### 1. Backend Service (FastAPI)
```bash
cd backend
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
pytest -v
python app/main.py
```
Backend API will run at `http://localhost:8000`.

### 2. Frontend Application (Vite + React)
```bash
cd frontend
npm install
npm run dev
```
Frontend web app will run at `http://localhost:3000`.

---

## 🐳 Docker Deployment

```bash
docker-compose up --build
```
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
