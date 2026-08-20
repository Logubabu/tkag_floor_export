# ETABS Integration Specification & Research

## 1. Overview
This document outlines the integration mechanisms between the Floor Exporter application and CSI ETABS building modeling software.

## 2. ETABS Access Mechanisms

### 2.1 ETABS `.E2K` Text File Export (Primary Web-Compatible Method)
- **Format**: Plaintext keyword-structured file (`.E2K` / `.S2K`).
- **Generation**: Generated from ETABS via `File -> Export -> ETABS .e2k Text File...`.
- **Platform Independence**: Can be uploaded and parsed on any operating system (Linux, macOS, Windows) inside containerized cloud microservices without requiring an ETABS license or active software installation on the web server.
- **Data Coverage**: Contains complete building geometry (STORIES, JOINTS, LINE ASSIGNS, AREA ASSIGNS), material definitions, frame section properties, wall/slab area properties, point/line/area loads, load patterns, and combinations.

### 2.2 ETABS Open API / COM Automation Interface (Windows Direct Bridge)
- **COM ProgIDs**:
  - `CSI.ETABS.API.ETABSObject`
  - `ETABSv1.ETABSObject`
  - `ETABS2016.ETABSObject`
  - `ETABSv18.ETABSObject` ... `ETABSv21.ETABSObject`
- **Helper Object**: `ETABSv1.Helper` (`GetObject("CSI.ETABS.API.ETABSObject")`)
- **Capabilities**: Directly queries story elevations, joint coordinates, frame objects (beams/columns/braces), area objects (slabs/walls/openings), section properties, and load assignments from an actively running ETABS session.
- **Requirement**: Requires Windows OS with registered CSI ETABS installation and COM API DLLs.

### 2.3 Binary `.EDB` File Disclaimer
- **Important**: `.EDB` is a proprietary binary database file format owned by Computers and Structures, Inc. (CSI). Direct reading of `.EDB` files without the official CSI ETABS API runtime is not natively supported by standard open-source Python libraries.
- The web app accepts `.E2K` files, pre-parsed JSON models, or direct COM connections on Windows systems.

---

## 3. Structural Element Extraction Mapping

| ETABS Object | Web App Intermediate Model | Key Attributes Extracted |
| :--- | :--- | :--- |
| `Story` | `Story` | `id`, `name`, `elevation`, `height`, `is_master` |
| `PointObj` / `Joint` | `Node` | `id`, `x`, `y`, `z`, `restraints` |
| `FrameObj` (Beam) | `Frame` (Beam) | `id`, `section`, `start_node`, `end_node`, `story`, `material` |
| `FrameObj` (Column) | `Frame` (Column) | `id`, `section`, `start_node`, `end_node`, `story`, `material` |
| `AreaObj` (Slab) | `Slab` | `id`, `property`, `thickness`, `polygon`, `story`, `material` |
| `AreaObj` (Wall) | `Wall` | `id`, `property`, `thickness`, `polygon`, `story`, `material` |
| `AreaObj` (Opening)| `Slab` (Opening) | `id`, `is_opening`, `polygon`, `story` |
| `LoadPattern` | `LoadPattern` | `name`, `type`, `self_weight_multiplier` |
| `AreaLoad` | `AreaLoad` | `area_id`, `pattern`, `value`, `units` |

---

## 4. Coordinate System Conventions
- **ETABS Coordinates**:
  - Global X: Rightward / Easting (m or mm or ft)
  - Global Y: Upward / Northing (m or mm or ft)
  - Global Z: Vertical Elevation (m or mm or ft)
- **Internal Web Engine Coordinates**:
  - Normalized to SI Units (Meters `m` for geometry, Kilonewtons `kN` for forces, Megapascals `MPa` for stress).
  - Standard origin offset applied per project configuration.
