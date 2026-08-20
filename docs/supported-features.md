# Supported Structural Features & Limitations Matrix

## 1. Supported ETABS Elements & Mapping

| ETABS Feature | Support Level | Intermediate Model Representation | RAM Concept Output Mapping |
| :--- | :--- | :--- | :--- |
| **Story Levels** | Full | `Story` (Elevation, Height) | Story elevations & reference planes |
| **Joints / Nodes** | Full | `Node` (X, Y, Z, Restraints) | Node coordinates & point supports |
| **Slabs** | Full | `Slab` (Polygon, Thickness, Material) | `SLAB_OUTLINE` DXF polyline |
| **Slab Openings** | Full | `Slab.is_opening` (Polygon) | `OPENINGS` DXF polyline |
| **Beams** | Full | `Frame` (Beams: Start Node, End Node, Section) | `BEAMS` DXF line / polyline |
| **Columns Above / Below** | Full | `Frame` (Columns: Top Node, Bottom Node, Section) | `COLUMNS_ABOVE` & `COLUMNS_BELOW` DXF point/polyline |
| **Walls Above / Below** | Full | `Wall` (Polygon / Line, Thickness, Material) | `WALLS_ABOVE` & `WALLS_BELOW` DXF line/polyline |
| **Concrete Materials** | Full | `Material` (fc, E, Poisson's ratio) | Material property definitions |
| **Area Uniform Loads** | Full | `AreaLoad` (Pattern, Value, Direction) | `SURFACE_LOADS` DXF polyline |
| **Point Loads** | Full | `PointLoad` (Joint, Pattern, Fz, Mx, My) | `POINT_LOADS` DXF point |
| **Line Loads** | Full | `LineLoad` (Frame, Pattern, Value) | `LINE_LOADS` DXF line |

## 2. Current MVP Limitations & Future Roadmap

- **Post-Tensioning (PT) Tendons**: ETABS PT tendons can be viewed in 3D; direct tendon export to RAM Concept PT profile objects will be expanded in v2.0.
- **Ramp & Inclined Slabs**: Slabs with non-horizontal Z elevations are flattened onto the story plane with elevation delta warnings during RAM Concept export.
- **Complex Curved Polylines**: Curved edges are discretized into piecewise linear segments during E2K parsing and geometry validation.
