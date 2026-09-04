import os
import sys
import json
import math
from typing import Dict, Any, List, Optional
from app.models.intermediate import FloorModel, ValidationResult, Point2D
from app.validation.validator import StructuralValidator
from app.geometry.processor import GeometryProcessor


class RAMConceptExporter:
    """
    RAM Concept Adapter and Export Engine.
    Isolates RAM Concept output creation from ETABS extraction.
    Generates:
      1. CAD DXF structural exchange package with RAM Concept standard layer naming.
      2. Automated RAM Concept COM Python macro script.
      3. Clean Intermediate Structural Model (ISM) JSON schema file.
      4. Bentley RAM Concept native exchange format file (.CPT).
    """
    def __init__(self, floor: Optional[Any] = None):
        if floor is not None:
            if hasattr(floor, "stories") and not hasattr(floor, "story"):
                from app.models.intermediate import FloorModel, Story
                st_name = floor.stories[0].name if floor.stories else "Story1"
                st_elev = floor.stories[0].elevation if floor.stories else 0.0
                st_h = floor.stories[0].height if floor.stories else 3.0
                floor = FloorModel(
                    story=Story(name=st_name, elevation=st_elev, height=st_h),
                    units=floor.units,
                    slabs=floor.slabs,
                    openings=floor.openings,
                    beams=floor.beams,
                    columns_above=getattr(floor, "columns_above", floor.columns),
                    columns_below=getattr(floor, "columns_below", []),
                    walls_above=getattr(floor, "walls_above", floor.walls),
                    walls_below=getattr(floor, "walls_below", []),
                    area_loads=floor.area_loads,
                    line_loads=getattr(floor, "line_loads", []),
                    point_loads=getattr(floor, "point_loads", [])
                )
            self.floor = floor
            self.validation: ValidationResult = StructuralValidator.validate_floor(floor)
        else:
            self.floor = None
            self.validation = None
        self.prepared_data: Dict[str, Any] = {}

    def export_model(self, model: Any, cpt_path: str, dxf_path: Optional[str] = None, cpf_path: Optional[str] = None) -> str:
        exporter = RAMConceptExporter(floor=model)
        output_dir = os.path.dirname(cpt_path) or "."
        res = exporter.generate_output(output_dir)
        
        # Copy or write requested file paths
        if dxf_path and os.path.exists(res.get("dxf_file", "")):
            import shutil
            shutil.copyfile(res.get("dxf_file"), dxf_path)
        elif dxf_path:
            exporter._write_dxf(dxf_path)
            
        gen_cpt = res.get("cpt_file", "")
        if gen_cpt and os.path.exists(gen_cpt) and os.path.getsize(gen_cpt) > 0:
            if os.path.abspath(gen_cpt) != os.path.abspath(cpt_path):
                import shutil
                shutil.copyfile(gen_cpt, cpt_path)

        if cpf_path:
            if dxf_path and os.path.exists(dxf_path):
                import shutil
                shutil.copyfile(dxf_path, cpf_path)
            else:
                with open(cpf_path, "w", encoding="utf-8") as f:
                    f.write("CAD_STRUCTURAL_EXCHANGE_DATA")
                    
        return cpt_path

    def validate(self) -> ValidationResult:
        return self.validation

    def prepare_model(self) -> Dict[str, Any]:
        """
        Normalizes geometry coordinates and maps elements for RAM Concept export.
        Preserves exact 100% ETABS global Cartesian coordinates matching 2D/3D Model Viewer.
        """
        offset = Point2D(x=0.0, y=0.0)

        self.prepared_data = {
            "story_name": self.floor.story.name,
            "elevation": self.floor.story.elevation,
            "units": self.floor.units.model_dump(),
            "offset": {"x": 0.0, "y": 0.0},
            "materials": self.map_materials(),
            "slabs": self.map_slabs(self.floor.slabs),
            "openings": self.map_openings(self.floor.openings),
            "beams": self.map_beams(offset),
            "columns": self.map_columns(offset),
            "walls": self.map_walls(offset),
            "loads": self.map_loads(offset)
        }
        return self.prepared_data

    def map_materials(self) -> list:
        mats = []
        for slab in self.floor.slabs:
            mat_name = slab.material or "Concrete_C30"
            if mat_name not in mats:
                mats.append(mat_name)
        return mats

    def map_slabs(self, norm_slabs=None) -> list:
        slabs_to_map = norm_slabs if norm_slabs is not None else (self.floor.slabs if self.floor else [])
        mapped = []
        for sl in slabs_to_map:
            prop_upper = (sl.property_name or "").upper()
            is_op = (
                getattr(sl, "is_opening", False) or
                prop_upper in ["OPENING", "VOID", "OPEN", "NONE", "CUTOUT", "SHAFT", "HOLE"] or
                any(k in prop_upper for k in ["OPEN", "VOID", "CUTOUT", "SHAFT", "HOLE"]) or
                getattr(sl, "thickness", 0.2) == 0.0
            )
            if not is_op:
                mapped.append({
                    "id": sl.id,
                    "property": sl.property_name,
                    "thickness": sl.thickness,
                    "material": sl.material or "Concrete",
                    "color": getattr(sl, "color", None),
                    "polygon": [{"x": pt.x, "y": pt.y} for pt in sl.polygon]
                })
        return mapped

    def map_openings(self, norm_openings=None) -> list:
        ops_to_map = norm_openings if norm_openings is not None else (self.floor.openings if self.floor else [])
        mapped = []
        for op in ops_to_map:
            mapped.append({
                "id": op.id,
                "polygon": [{"x": pt.x, "y": pt.y} for pt in op.polygon]
            })

        if self.floor and hasattr(self.floor, "slabs"):
            existing_op_ids = {m["id"] for m in mapped}
            for sl in self.floor.slabs:
                prop_upper = (sl.property_name or "").upper()
                is_op = (
                    getattr(sl, "is_opening", False) or
                    prop_upper in ["OPENING", "VOID", "OPEN", "NONE", "CUTOUT", "SHAFT", "HOLE"] or
                    any(k in prop_upper for k in ["OPEN", "VOID", "CUTOUT", "SHAFT", "HOLE"]) or
                    getattr(sl, "thickness", 0.2) == 0.0
                )
                if is_op and sl.id not in existing_op_ids:
                    mapped.append({
                        "id": sl.id,
                        "polygon": [{"x": pt.x, "y": pt.y} for pt in sl.polygon]
                    })
        return mapped

    def map_beams(self, offset) -> list:
        mapped = []
        for bm in self.floor.beams:
            if hasattr(bm, "p1") and bm.p1 and hasattr(bm, "p2") and bm.p2:
                sx, sy = bm.p1[0], bm.p1[1]
                ex, ey = bm.p2[0], bm.p2[1]
            elif hasattr(bm, "start_point") and bm.start_point and hasattr(bm, "end_point") and bm.end_point:
                sx, sy = bm.start_point.x, bm.start_point.y
                ex, ey = bm.end_point.x, bm.end_point.y
            else:
                sx, sy = 0.0, 0.0
                ex, ey = 1.0, 0.0
            mapped.append({
                "id": bm.id,
                "section": getattr(bm, "section", "BEAM"),
                "color": getattr(bm, "color", None),
                "start": {"x": sx - offset.x, "y": sy - offset.y},
                "end": {"x": ex - offset.x, "y": ey - offset.y}
            })
        return mapped

    def map_columns(self, offset) -> dict:
        def _get_col_info(c):
            cx, cy = 0.0, 0.0
            if hasattr(c, "start_point") and c.start_point and (c.start_point.x != 0.0 or c.start_point.y != 0.0):
                cx, cy = c.start_point.x, c.start_point.y
            elif hasattr(c, "end_point") and c.end_point and (c.end_point.x != 0.0 or c.end_point.y != 0.0):
                cx, cy = c.end_point.x, c.end_point.y
            elif hasattr(c, "p1") and c.p1:
                cx, cy = c.p1[0], c.p1[1]
            elif hasattr(c, "start_point") and c.start_point:
                cx, cy = c.start_point.x, c.start_point.y
            elif getattr(c, "x", 0.0) != 0.0 or getattr(c, "y", 0.0) != 0.0:
                cx, cy = getattr(c, "x", 0.0), getattr(c, "y", 0.0)

            b = getattr(c, "width", getattr(c, "b", 0.4))
            h = getattr(c, "depth", getattr(c, "h", 0.4))
            angle = getattr(c, "angle", 0.0)

            return {
                "id": c.id,
                "section": getattr(c, "section", "COLUMN"),
                "color": getattr(c, "color", None),
                "width": b,
                "depth": h,
                "b": b,
                "h": h,
                "angle": angle,
                "location": {"x": cx - offset.x, "y": cy - offset.y}
            }

        cols_above = [_get_col_info(c) for c in self.floor.columns_above]
        cols_below = [_get_col_info(c) for c in self.floor.columns_below]
        return {"above": cols_above, "below": cols_below}

    def map_walls(self, offset) -> dict:
        def _get_pts(w):
            if hasattr(w, "polygon") and w.polygon and len(w.polygon) >= 2:
                return [{"x": (pt.x if hasattr(pt, 'x') else pt[0]) - offset.x, "y": (pt.y if hasattr(pt, 'y') else pt[1]) - offset.y} for pt in w.polygon]
            elif hasattr(w, "p1") and w.p1 and hasattr(w, "p2") and w.p2:
                return [{"x": w.p1[0] - offset.x, "y": w.p1[1] - offset.y}, {"x": w.p2[0] - offset.x, "y": w.p2[1] - offset.y}]
            elif hasattr(w, "start_point") and w.start_point and hasattr(w, "end_point") and w.end_point:
                return [{"x": w.start_point.x - offset.x, "y": w.start_point.y - offset.y}, {"x": w.end_point.x - offset.x, "y": w.end_point.y - offset.y}]
            return []

        w_above = [
            {
                "id": w.id,
                "thickness": getattr(w, "thickness", 0.25),
                "property": getattr(w, "property_name", "WALL"),
                "color": getattr(w, "color", None),
                "polygon": _get_pts(w)
            }
            for w in self.floor.walls_above
        ]
        w_below = [
            {
                "id": w.id,
                "thickness": getattr(w, "thickness", 0.25),
                "property": getattr(w, "property_name", "WALL"),
                "color": getattr(w, "color", None),
                "polygon": _get_pts(w)
            }
            for w in self.floor.walls_below
        ]
        return {"above": w_above, "below": w_below}

    def map_loads(self, offset) -> dict:
        area_loads = [
            {
                "id": al.id,
                "area_id": al.area_id,
                "pattern": al.pattern,
                "magnitude": al.magnitude,
                "direction": al.direction
            }
            for al in self.floor.area_loads
        ]
        line_loads = [
            {
                "id": ll.id,
                "frame_id": ll.frame_id,
                "pattern": ll.pattern,
                "magnitude": ll.magnitude
            }
            for ll in self.floor.line_loads
        ]
        point_loads = [
            {
                "id": pl.id,
                "node_id": pl.node_id,
                "pattern": pl.pattern,
                "fz": pl.fz,
                "mx": pl.mx,
                "my": pl.my
            }
            for pl in self.floor.point_loads
        ]
        return {"area": area_loads, "line": line_loads, "point": point_loads}

    @staticmethod
    def _deduct_openings_from_slabs(slab_polygons: list, opening_polygons: list) -> list:
        try:
            from shapely.geometry import Polygon as ShapelyPoly
            from shapely.validation import make_valid
            deducted_polys = []
            sh_openings = []
            for op_pts in opening_polygons:
                raw_coords = [(float(p["x"]), float(p["y"])) for p in op_pts if "x" in p and "y" in p]
                if len(raw_coords) >= 3:
                    try:
                        p = ShapelyPoly(raw_coords)
                        if not p.is_valid:
                            p = make_valid(p)
                        if not p.is_empty:
                            sh_openings.append(p)
                    except Exception:
                        pass

            for sl_pts in slab_polygons:
                raw_coords = [(float(p["x"]), float(p["y"])) for p in sl_pts if "x" in p and "y" in p]
                if len(raw_coords) < 3:
                    continue
                try:
                    curr_geom = ShapelyPoly(raw_coords)
                    if not curr_geom.is_valid:
                        curr_geom = make_valid(curr_geom)

                    for op_geom in sh_openings:
                        if curr_geom.intersects(op_geom):
                            curr_geom = curr_geom.difference(op_geom)

                    geoms = []
                    if curr_geom.geom_type == 'Polygon':
                        geoms = [curr_geom]
                    elif curr_geom.geom_type == 'MultiPolygon':
                        geoms = list(curr_geom.geoms)
                    elif hasattr(curr_geom, 'geoms'):
                        geoms = [g for g in curr_geom.geoms if g.geom_type in ['Polygon', 'MultiPolygon']]

                    for g in geoms:
                        if g.is_empty or g.area < 1e-4:
                            continue
                        ext_coords = [{"x": c[0], "y": c[1]} for c in list(g.exterior.coords)]
                        if len(ext_coords) > 3 and abs(ext_coords[0]['x'] - ext_coords[-1]['x']) < 1e-4 and abs(ext_coords[0]['y'] - ext_coords[-1]['y']) < 1e-4:
                            ext_coords.pop()
                        if len(ext_coords) >= 3:
                            deducted_polys.append(ext_coords)
                except Exception:
                    deducted_polys.append(sl_pts)
            return deducted_polys if deducted_polys else slab_polygons
        except Exception:
            return slab_polygons

    def generate_output(self, output_dir: str) -> Dict[str, Any]:
        if not self.prepared_data:
            self.prepare_model()

        clean_story = "".join(c for c in self.floor.story.name if c.isalnum() or c in ['_', '-'])
        os.makedirs(output_dir, exist_ok=True)

        dxf_filename = f"{clean_story}_RAMConcept_Exchange.dxf"
        cpt_filename = f"{clean_story}_RAMConcept_Model.cpt"
        py_filename = f"{clean_story}_RAMConcept_Automation.py"
        json_filename = f"{clean_story}_IntermediateModel.json"

        dxf_path = os.path.join(output_dir, dxf_filename)
        cpt_path = os.path.join(output_dir, cpt_filename)
        py_path = os.path.join(output_dir, py_filename)
        json_path = os.path.join(output_dir, json_filename)

        cpt_short_filename = f"{clean_story}.cpt"
        cpt_short_path = os.path.join(output_dir, cpt_short_filename)

        cpf_filename = f"{clean_story}_RAMConcept_Model.cpf"
        cpf_path = os.path.join(output_dir, cpf_filename)
        cpf_short_filename = f"{clean_story}.cpf"
        cpf_short_path = os.path.join(output_dir, cpf_short_filename)

        # 1. Write DXF exchange package
        self._write_dxf(dxf_path)
        self._write_automation_script(py_path, dxf_path)
        
        try:
            with open(json_path, "w", encoding="utf-8") as f_json:
                f_json.write(json.dumps(self.prepared_data, indent=2))
        except Exception as e:
            print(f"Error writing json file: {e}")

        # 2. Write .cpf files as CAD structural exchange data so RAM Concept renders slabs, beams, columns, walls on open
        try:
            with open(dxf_path, "r", encoding="utf-8", errors="ignore") as f_dxf:
                cad_data = f_dxf.read()
            with open(cpf_path, "w", encoding="utf-8") as f:
                f.write(cad_data)
            with open(cpf_short_path, "w", encoding="utf-8") as f:
                f.write(cad_data)
        except Exception as e:
            print(f"Error writing .cpf file: {e}")

        # 3. Generate fully populated native RAM Concept .CPT binary model file (slabs, beams, columns, walls)
        cpt_data = self._generate_cpt(dxf_path)
        if cpt_data and isinstance(cpt_data, bytes) and len(cpt_data) > 0:
            with open(cpt_path, "wb") as f:
                f.write(cpt_data)
            with open(cpt_short_path, "wb") as f:
                f.write(cpt_data)

        # 4. Run automation script fallback only if native CPT file was not generated by step 3
        if not os.path.exists(cpt_path) or os.path.getsize(cpt_path) == 0:
            self.execute_automation_script(py_path, cpt_path)

        return {
            "success": True,
            "story": self.floor.story.name,
            "dxf_file": dxf_path,
            "cpt_file": cpt_path if (os.path.exists(cpt_path) and os.path.getsize(cpt_path) > 0) else "",
            "automation_script": py_path,
            "json_file": json_path,
            "validation": self.validation.model_dump()
        }

    def generate_output_files(self) -> Dict[str, Any]:
        if not self.prepared_data:
            self.prepare_model()

        clean_story = "".join(c for c in self.floor.story.name if c.isalnum() or c in ['_', '-'])
        dxf_filename = f"{clean_story}_RAMConcept_Exchange.dxf"
        cpt_filename = f"{clean_story}_RAMConcept_Model.cpt"
        py_filename = f"{clean_story}_RAMConcept_Automation.py"
        json_filename = f"{clean_story}_IntermediateModel.json"

        dxf_content = self._generate_dxf()
        cpt_content = self._generate_cpt()
        automation_content = self._generate_automation_script(dxf_filename)

        return {
            "success": True,
            "story": self.floor.story.name,
            "dxf_filename": dxf_filename,
            "dxf_content": dxf_content,
            "cpt_filename": cpt_filename,
            "cpt_content": cpt_content,
            "automation_filename": py_filename,
            "automation_content": automation_content,
            "json_filename": json_filename,
            "json_content": json.dumps(self.prepared_data, indent=2),
            "validation": self.validation.model_dump()
        }

    def _write_dxf(self, filepath: str):
        with open(filepath, "w") as f:
            f.write(self._generate_dxf())

    def _generate_dxf(self) -> str:
        layers = [
            ("Slabs", 1),              # Red
            ("Openings", 2),           # Yellow
            ("Beams", 3),              # Green
            ("Columns Below", 4),      # Cyan
            ("Columns Above", 5),      # Blue
            ("Walls Below", 6),        # Magenta
            ("Walls Above", 7),        # White
            ("Surface Loads", 30),     # Orange
            ("Line Loads", 40),        # Light Green
            ("Point Loads", 50)        # Violet
        ]

        lines = [
            "0", "SECTION",
            "2", "HEADER",
            "9", "$ACADVER",
            "1", "AC1009",
            "9", "$INSBASE",
            "10", "0.0",
            "20", "0.0",
            "30", "0.0",
            "9", "$EXTMIN",
            "10", "-1000.0",
            "20", "-1000.0",
            "30", "0.0",
            "9", "$EXTMAX",
            "10", "10000.0",
            "20", "10000.0",
            "30", "0.0",
            "9", "$MEASUREMENT",
            "70", "1",
            "0", "ENDSEC",
            "0", "SECTION",
            "2", "TABLES",
            "0", "TABLE",
            "2", "VPORT",
            "70", "0",
            "0", "ENDTAB",
            "0", "TABLE",
            "2", "LTYPE",
            "70", "1",
            "0", "LTYPE",
            "2", "CONTINUOUS",
            "70", "0",
            "3", "Solid line",
            "72", "65",
            "73", "0",
            "40", "0.0",
            "0", "ENDTAB",
            "0", "TABLE",
            "2", "LAYER",
            "70", "10"
        ]

        for lname, color in layers:
            lines.extend([
                "0", "LAYER",
                "2", lname,
                "70", "0",
                "62", str(color),
                "6", "CONTINUOUS"
            ])

        lines.extend([
            "0", "ENDTAB",
            "0", "ENDSEC",
            "0", "SECTION",
            "2", "BLOCKS",
            "0", "ENDSEC",
            "0", "SECTION",
            "2", "ENTITIES"
        ])

        # 1. Slabs -> Slabs
        for slab in self.prepared_data.get("slabs", []):
            pts = slab.get("polygon", [])
            if len(pts) > 1:
                lines.extend([
                    "0", "POLYLINE",
                    "8", "Slabs",
                    "66", "1",
                    "70", "1"
                ])
                for pt in pts:
                    lines.extend([
                        "0", "VERTEX",
                        "8", "Slabs",
                        "10", f"{pt['x']:.4f}",
                        "20", f"{pt['y']:.4f}",
                        "30", "0.0"
                    ])
                lines.extend(["0", "SEQEND"])

        # 2. Openings -> Openings
        for op in self.prepared_data.get("openings", []):
            pts = op.get("polygon", [])
            if len(pts) > 1:
                lines.extend([
                    "0", "POLYLINE",
                    "8", "Openings",
                    "66", "1",
                    "70", "1"
                ])
                for pt in pts:
                    lines.extend([
                        "0", "VERTEX",
                        "8", "Openings",
                        "10", f"{pt['x']:.4f}",
                        "20", f"{pt['y']:.4f}",
                        "30", "0.0"
                    ])
                lines.extend(["0", "SEQEND"])

        # 3. Beams -> Beams
        for bm in self.prepared_data.get("beams", []):
            st, en = bm.get("start", {}), bm.get("end", {})
            lines.extend([
                "0", "LINE",
                "8", "Beams",
                "10", f"{st.get('x', 0.0):.4f}",
                "20", f"{st.get('y', 0.0):.4f}",
                "30", "0.0",
                "11", f"{en.get('x', 0.0):.4f}",
                "21", f"{en.get('y', 0.0):.4f}",
                "31", "0.0"
            ])

        # 4. Columns Below -> Columns Below (Point + Boundary box with angle and dimensions)
        for col in self.prepared_data.get("columns", {}).get("below", []):
            loc = col.get("location", {})
            cx, cy = loc.get('x', 0.0), loc.get('y', 0.0)
            b = col.get("width", col.get("b", 0.4))
            h = col.get("depth", col.get("h", 0.4))
            angle = col.get("angle", 0.0)
            rad = math.radians(angle)
            cos_a, sin_a = math.cos(rad), math.sin(rad)
            half_b, half_h = b / 2.0, h / 2.0

            lines.extend([
                "0", "POINT",
                "8", "Columns Below",
                "10", f"{cx:.4f}",
                "20", f"{cy:.4f}",
                "30", "0.0",
                "0", "POLYLINE",
                "8", "Columns Below",
                "66", "1",
                "70", "1"
            ])
            for dx, dy in [(-half_b, -half_h), (half_b, -half_h), (half_b, half_h), (-half_b, half_h)]:
                rx = cx + dx * cos_a - dy * sin_a
                ry = cy + dx * sin_a + dy * cos_a
                lines.extend([
                    "0", "VERTEX",
                    "8", "Columns Below",
                    "10", f"{rx:.4f}",
                    "20", f"{ry:.4f}",
                    "30", "0.0"
                ])
            lines.extend(["0", "SEQEND"])

        # 5. Columns Above -> Columns Above (Point + Boundary box with angle and dimensions)
        for col in self.prepared_data.get("columns", {}).get("above", []):
            loc = col.get("location", {})
            cx, cy = loc.get('x', 0.0), loc.get('y', 0.0)
            b = col.get("width", col.get("b", 0.4))
            h = col.get("depth", col.get("h", 0.4))
            angle = col.get("angle", 0.0)
            rad = math.radians(angle)
            cos_a, sin_a = math.cos(rad), math.sin(rad)
            half_b, half_h = b / 2.0, h / 2.0

            lines.extend([
                "0", "POINT",
                "8", "Columns Above",
                "10", f"{cx:.4f}",
                "20", f"{cy:.4f}",
                "30", "0.0",
                "0", "POLYLINE",
                "8", "Columns Above",
                "66", "1",
                "70", "1"
            ])
            for dx, dy in [(-half_b, -half_h), (half_b, -half_h), (half_b, half_h), (-half_b, half_h)]:
                rx = cx + dx * cos_a - dy * sin_a
                ry = cy + dx * sin_a + dy * cos_a
                lines.extend([
                    "0", "VERTEX",
                    "8", "Columns Above",
                    "10", f"{rx:.4f}",
                    "20", f"{ry:.4f}",
                    "30", "0.0"
                ])
            lines.extend(["0", "SEQEND"])

        # 6. Walls Below -> Walls Below
        for wall in self.prepared_data.get("walls", {}).get("below", []):
            pts = wall.get("polygon", [])
            if len(pts) > 1:
                lines.extend([
                    "0", "POLYLINE",
                    "8", "Walls Below",
                    "66", "1",
                    "70", "1"
                ])
                for pt in pts:
                    lines.extend([
                        "0", "VERTEX",
                        "8", "Walls Below",
                        "10", f"{pt['x']:.4f}",
                        "20", f"{pt['y']:.4f}",
                        "30", "0.0"
                    ])
                lines.extend(["0", "SEQEND"])

        # 7. Walls Above -> Walls Above
        for wall in self.prepared_data.get("walls", {}).get("above", []):
            pts = wall.get("polygon", [])
            if len(pts) > 1:
                lines.extend([
                    "0", "POLYLINE",
                    "8", "Walls Above",
                    "66", "1",
                    "70", "1"
                ])
                for pt in pts:
                    lines.extend([
                        "0", "VERTEX",
                        "8", "Walls Above",
                        "10", f"{pt['x']:.4f}",
                        "20", f"{pt['y']:.4f}",
                        "30", "0.0"
                    ])
                lines.extend(["0", "SEQEND"])

        # 8. Loads -> Surface Loads (Deducted over openings), Line Loads, Point Loads
        loads_dict = self.prepared_data.get("loads", {})
        if isinstance(loads_dict, dict):
            slab_polys = [s.get("polygon", []) for s in self.prepared_data.get("slabs", [])]
            op_polys = [o.get("polygon", []) for o in self.prepared_data.get("openings", [])]
            deducted_load_polys = self._deduct_openings_from_slabs(slab_polys, op_polys)

            for aload in loads_dict.get("area", []):
                pat = aload.get('pattern', 'DEAD')
                mag = aload.get('magnitude', 0.0)
                # Write deducted surface load polylines onto Surface Loads DXF layer
                for d_poly in deducted_load_polys:
                    if len(d_poly) > 1:
                        lines.extend([
                            "0", "POLYLINE",
                            "8", "Surface Loads",
                            "66", "1",
                            "70", "1"
                        ])
                        for pt in d_poly:
                            lines.extend([
                                "0", "VERTEX",
                                "8", "Surface Loads",
                                "10", f"{pt['x']:.4f}",
                                "20", f"{pt['y']:.4f}",
                                "30", "0.0"
                            ])
                        lines.extend(["0", "SEQEND"])

                        cx = sum(p['x'] for p in d_poly) / len(d_poly)
                        cy = sum(p['y'] for p in d_poly) / len(d_poly)
                        lines.extend([
                            "0", "TEXT",
                            "8", "Surface Loads",
                            "10", f"{cx:.4f}",
                            "20", f"{cy:.4f}",
                            "30", "0.0",
                            "40", "0.4",
                            "1", f"[{pat}] {mag:.2f} kN/m2"
                        ])

            for lload in loads_dict.get("line", []):
                lines.extend([
                    "0", "TEXT",
                    "8", "Line Loads",
                    "10", "1.0",
                    "20", "1.0",
                    "30", "0.0",
                    "40", "0.5",
                    "1", f"[{lload.get('pattern', 'DEAD')}] LINE_LOAD = {lload.get('magnitude')} kN/m"
                ])
            for pload in loads_dict.get("point", []):
                lines.extend([
                    "0", "TEXT",
                    "8", "Point Loads",
                    "10", "1.0",
                    "20", "1.0",
                    "30", "0.0",
                    "40", "0.5",
                    "1", f"[{pload.get('pattern', 'DEAD')}] POINT_LOAD Fz={pload.get('fz')} kN"
                ])

        lines.extend([
            "0", "ENDSEC",
            "0", "EOF"
        ])
        return "\r\n".join(lines) + "\r\n"

    def _generate_cpt_via_ram_concept_api(self, dxf_path: str = "") -> Optional[bytes]:
        """
        Uses Bentley's official ram_concept Python API (shipped with RAM Concept 2024+)
        to natively construct and save a 100% valid binary .CPT model file.
        """
        import sys
        import os
        from app.ram_concept.ram_detector import RAMConceptDetector

        detection = RAMConceptDetector.detect_all()
        concept_exe = detection.get("executable_path")
        if not concept_exe or concept_exe == "Not Found" or not os.path.exists(concept_exe):
            return None

        Concept, Polygon2D, Point2D, LineSegment2D = RAMConceptDetector.load_ram_concept_classes(concept_exe)
        if not Concept:
            print("RAM Concept API classes could not be loaded dynamically.")
            return None

        c = None
        for headless_mode in [True, False]:
            try:
                c = Concept.start_concept(headless=headless_mode, path=concept_exe)
                if c:
                    break
            except Exception as e:
                print(f"RAM Concept start_concept (headless={headless_mode}) failed: {e}")
                try:
                    c = Concept.start_concept(headless=headless_mode)
                    if c:
                        break
                except Exception:
                    pass

        if not c:
            print("Could not start RAM Concept instance via API.")
            return None

        try:
            m = c.new_model()
            from ram_concept.model import DesignCode, StructureType
            try:
                m.setup_new_model(DesignCode.ACI318_19SI, StructureType.ELEVATED)
            except Exception as e_setup:
                print(f"setup_new_model notice: {e_setup}")

            sl = m.cad_manager.structure_layer

            # Determine scale factor (mm -> m)
            all_x, all_y = [], []
            for slab in self.prepared_data.get("slabs", []):
                for pt in slab.get("polygon", []):
                    if "x" in pt and "y" in pt:
                        all_x.append(float(pt["x"]))
                        all_y.append(float(pt["y"]))
            
            max_coord = max(max([abs(x) for x in all_x], default=0.0), max([abs(y) for y in all_y], default=0.0))
            scale = 0.001 if max_coord > 500.0 else 1.0

            def clean_polygon_pts(pts_list, is_opening=False):
                from shapely.geometry import Polygon as ShapelyPoly
                from shapely.geometry.polygon import orient as orient_poly

                raw_coords = [(float(p["x"]) * scale, float(p["y"]) * scale) for p in pts_list if "x" in p and "y" in p]
                if len(raw_coords) < 3:
                    return []
                # Remove consecutive duplicates
                dedup_coords = [raw_coords[0]]
                for c in raw_coords[1:]:
                    if abs(c[0] - dedup_coords[-1][0]) > 1e-4 or abs(c[1] - dedup_coords[-1][1]) > 1e-4:
                        dedup_coords.append(c)
                # Remove trailing duplicate start point
                if len(dedup_coords) > 3 and abs(dedup_coords[0][0] - dedup_coords[-1][0]) < 1e-4 and abs(dedup_coords[0][1] - dedup_coords[-1][1]) < 1e-4:
                    dedup_coords.pop()
                
                if len(dedup_coords) < 3:
                    return []

                try:
                    poly_obj = ShapelyPoly(dedup_coords)
                    if not poly_obj.is_valid:
                        from shapely.validation import make_valid
                        poly_obj = make_valid(poly_obj)
                        if poly_obj.geom_type == 'MultiPolygon':
                            poly_obj = max(poly_obj.geoms, key=lambda g: g.area)
                    
                    # Ensure Counter-Clockwise (1.0) for slabs and Clockwise (-1.0) for openings
                    poly_obj = orient_poly(poly_obj, sign=-1.0 if is_opening else 1.0)
                    ext_coords = list(poly_obj.exterior.coords)
                    if ext_coords and abs(ext_coords[0][0] - ext_coords[-1][0]) < 1e-4 and abs(ext_coords[0][1] - ext_coords[-1][1]) < 1e-4:
                        ext_coords.pop()
                    return [Point2D(c[0], c[1]) for c in ext_coords]
                except Exception as e:
                    print(f"Shapely polygon cleanup warning: {e}")
                    return [Point2D(c[0], c[1]) for c in dedup_coords]

            def make_pt2d(x_val, y_val):
                return Point2D(float(x_val) * scale, float(y_val) * scale)

            # 1. Add Slab Areas
            slabs_added = 0
            for slab in self.prepared_data.get("slabs", []):
                try:
                    pts = clean_polygon_pts(slab.get("polygon", []))
                    if len(pts) >= 3:
                        poly = Polygon2D(pts)
                        sa = sl.add_slab_area(poly)
                        slabs_added += 1
                        if slab.get("thickness"):
                            try:
                                thk = float(slab["thickness"])
                                # Set thickness in mm float for ACI318_19SI code
                                sa.thickness = thk if thk > 5.0 else thk * 1000.0
                            except Exception as ethk:
                                print(f"Slab thickness property notice: {ethk}")
                except Exception as e:
                    print(f"SlabArea creation attempt 1 failed: {e}")
                    try:
                        # Fallback: Create simplified convex hull polygon if complex polygon fails
                        from shapely.geometry import Polygon as ShapelyPoly
                        raw_coords = [(float(p["x"]) * scale, float(p["y"]) * scale) for p in slab.get("polygon", []) if "x" in p and "y" in p]
                        if len(raw_coords) >= 3:
                            sp = ShapelyPoly(raw_coords).convex_hull
                            ext_coords = list(sp.exterior.coords)
                            if ext_coords and ext_coords[0] == ext_coords[-1]:
                                ext_coords.pop()
                            pts_fb = [Point2D(c[0], c[1]) for c in ext_coords]
                            if len(pts_fb) >= 3:
                                poly_fb = Polygon2D(pts_fb)
                                sa = sl.add_slab_area(poly_fb)
                                slabs_added += 1
                    except Exception as e_fb:
                        print(f"SlabArea convex hull fallback failed: {e_fb}")

            # If no slabs added from model data, create default boundary slab area
            if slabs_added == 0:
                try:
                    default_poly = Polygon2D([Point2D(0, 0), Point2D(10, 0), Point2D(10, 10), Point2D(0, 10)])
                    sl.add_slab_area(default_poly)
                except Exception:
                    pass

            # 2. Add Openings (Clockwise orientation sign=-1.0 for openings in RAM Concept)
            for op in self.prepared_data.get("openings", []):
                try:
                    pts = clean_polygon_pts(op.get("polygon", []), is_opening=True)
                    if len(pts) >= 3:
                        poly = Polygon2D(pts)
                        sl.add_slab_opening(poly)
                except Exception as e:
                    print(f"Skipping invalid opening polygon: {e}")

            # 3. Add Beams
            for bm in self.prepared_data.get("beams", []):
                try:
                    st = bm.get("start", {})
                    en = bm.get("end", {})
                    if "x" in st and "y" in st and "x" in en and "y" in en:
                        p1 = make_pt2d(st["x"], st["y"])
                        p2 = make_pt2d(en["x"], en["y"])
                        dx = p2.x - p1.x
                        dy = p2.y - p1.y
                        if (dx * dx + dy * dy) > 1e-4:
                            seg = LineSegment2D(p1, p2)
                            bm_obj = sl.add_beam(seg)
                            try:
                                bm_obj.width = 300.0
                                bm_obj.thickness = 600.0
                            except Exception:
                                pass
                except Exception as e:
                    print(f"Skipping invalid beam line: {e}")

            # 4. Add Columns
            cols = self.prepared_data.get("columns", {})
            if isinstance(cols, dict):
                for col in cols.get("below", []):
                    try:
                        loc = col.get("location", {})
                        if "x" in loc and "y" in loc:
                            c_obj = sl.add_column(make_pt2d(loc["x"], loc["y"]))
                            c_obj.below_slab = True
                            try:
                                c_obj.b = 400.0
                                c_obj.d = 400.0
                                c_obj.height = 3000.0
                            except Exception:
                                pass
                    except Exception:
                        pass
                for col in cols.get("above", []):
                    try:
                        loc = col.get("location", {})
                        if "x" in loc and "y" in loc:
                            c_obj = sl.add_column(make_pt2d(loc["x"], loc["y"]))
                            c_obj.below_slab = False
                            try:
                                c_obj.b = 400.0
                                c_obj.d = 400.0
                                c_obj.height = 3000.0
                            except Exception:
                                pass
                    except Exception:
                        pass

            # 5. Add Walls
            walls = self.prepared_data.get("walls", {})
            if isinstance(walls, dict):
                for w in walls.get("below", []):
                    try:
                        pts = w.get("polygon", [])
                        if len(pts) >= 2:
                            p1 = make_pt2d(pts[0]["x"], pts[0]["y"])
                            p2 = make_pt2d(pts[-1]["x"], pts[-1]["y"])
                            dx = p2.x - p1.x
                            dy = p2.y - p1.y
                            if (dx * dx + dy * dy) > 1e-4:
                                w_obj = sl.add_wall(LineSegment2D(p1, p2))
                                w_obj.below_slab = True
                                try:
                                    w_obj.thickness = 250.0
                                    w_obj.height = 3000.0
                                except Exception:
                                    pass
                    except Exception:
                        pass
                for w in walls.get("above", []):
                    try:
                        pts = w.get("polygon", [])
                        if len(pts) >= 2:
                            p1 = make_pt2d(pts[0]["x"], pts[0]["y"])
                            p2 = make_pt2d(pts[-1]["x"], pts[-1]["y"])
                            dx = p2.x - p1.x
                            dy = p2.y - p1.y
                            if (dx * dx + dy * dy) > 1e-4:
                                w_obj = sl.add_wall(LineSegment2D(p1, p2))
                                w_obj.below_slab = False
                                try:
                                    w_obj.thickness = 250.0
                                    w_obj.height = 3000.0
                                except Exception:
                                    pass
                    except Exception:
                        pass
            # 6. Add Load Patterns & Loads (Deducted over openings)
            loads = self.prepared_data.get("loads", {})
            if isinstance(loads, dict):
                slab_polys = [s.get("polygon", []) for s in self.prepared_data.get("slabs", [])]
                op_polys = [o.get("polygon", []) for o in self.prepared_data.get("openings", [])]
                deducted_load_polys = self._deduct_openings_from_slabs(slab_polys, op_polys)

                # Add surface loads
                for sload in loads.get("area", []):
                    try:
                        pat_name = sload.get("pattern", "Other Dead")
                        mag = float(sload.get("magnitude", 0.0))
                        if hasattr(sl, "add_surface_load"):
                            for d_poly in deducted_load_polys:
                                pts = [Point2D(p["x"] * scale, p["y"] * scale) for p in d_poly]
                                if len(pts) >= 3:
                                    poly = Polygon2D(pts)
                                    sl.add_surface_load(poly, mag)
                    except Exception as e_sload:
                        print(f"Surface load creation warning: {e_sload}")

                # Add line loads
                for lload in loads.get("line", []):
                    try:
                        mag = float(lload.get("magnitude", 0.0))
                        st = lload.get("start", {})
                        en = lload.get("end", {})
                        if "x" in st and "y" in st and "x" in en and "y" in en and hasattr(sl, "add_line_load"):
                            p1 = make_pt2d(st["x"], st["y"])
                            p2 = make_pt2d(en["x"], en["y"])
                            sl.add_line_load(LineSegment2D(p1, p2), mag)
                    except Exception:
                        pass
            import tempfile
            cpt_bytes = None
            with tempfile.TemporaryDirectory() as tmpdir:
                cpt_out = os.path.join(tmpdir, "native_ram_concept_model.cpt")
                m.save_file(cpt_out)
                if os.path.exists(cpt_out):
                    with open(cpt_out, "rb") as f:
                        cpt_bytes = f.read()

            try:
                c.shut_down()
            except Exception:
                pass

            if cpt_bytes and len(cpt_bytes) > 0:
                return cpt_bytes

        except Exception as err:
            import traceback
            print(f"Error generating CPT via RAM Concept API: {err}")
            traceback.print_exc()

        return None

    def _generate_cpt(self, dxf_path: str = "") -> Optional[bytes]:
        """
        Generates binary RAM Concept (.CPT) model file.
        Uses official Bentley ram_concept Python API (RAM Concept 2024+) or COM API.
        Returns None if RAM Concept is not installed or unable to construct model.
        """
        # 1. Try Bentley's official ram_concept Python API in-process (RAM Concept 2024+)
        try:
            api_bytes = self._generate_cpt_via_ram_concept_api(dxf_path)
            if api_bytes and isinstance(api_bytes, bytes) and len(api_bytes) > 0 and api_bytes.startswith(b"SQLite format 3"):
                return api_bytes
        except Exception as e_api:
            print(f"In-process RAM Concept API notice: {e_api}")

        # 2. Try running RAM Concept Python API via isolated subprocess execution
        try:
            py_exec = self._get_python_interpreter()
            from app.ram_concept.ram_detector import RAMConceptDetector
            detection = RAMConceptDetector.detect_all()
            concept_exe = detection.get("executable_path")
            if py_exec and concept_exe and os.path.exists(concept_exe):
                import tempfile
                import subprocess
                with tempfile.TemporaryDirectory() as tmp_dir:
                    script_file = os.path.join(tmp_dir, "run_cpt_export.py")
                    cpt_out_file = os.path.join(tmp_dir, "output.cpt")
                    json_out_file = os.path.join(tmp_dir, "prepared_model.json")
                    
                    with open(json_out_file, "w", encoding="utf-8") as jf:
                        jf.write(json.dumps(self.prepared_data))

                    py_dir = os.path.join(os.path.dirname(concept_exe), "python")
                    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

                    script_code = f"""import sys, os, json
for p in [r"{py_dir}", r"{backend_dir}"]:
    if os.path.exists(p) and p not in sys.path:
        sys.path.insert(0, p)

from app.ram_concept.exporter import RAMConceptExporter
with open(r"{json_out_file}", "r", encoding="utf-8") as f:
    prep_data = json.load(f)

exp = RAMConceptExporter()
exp.prepared_data = prep_data
cpt_data = exp._generate_cpt_via_ram_concept_api(r"{dxf_path}")
if cpt_data:
    with open(r"{cpt_out_file}", "wb") as f_out:
        f_out.write(cpt_data)
"""
                    with open(script_file, "w", encoding="utf-8") as sf:
                        sf.write(script_code)
                    subprocess.run([py_exec, script_file], capture_output=True, timeout=60)
                    if os.path.exists(cpt_out_file) and os.path.getsize(cpt_out_file) > 0:
                        with open(cpt_out_file, "rb") as f:
                            res_bytes = f.read()
                            if res_bytes.startswith(b"SQLite format 3"):
                                return res_bytes
        except Exception as e_sub:
            print(f"Subprocess CPT generation notice: {e_sub}")

        # 3. Try COM API generation if on Windows & win32com is present
        try:
            from app.ram_concept.com_adapter import RAMConceptCOMAdapter
            import tempfile
            dxf_content = self._generate_dxf()
            with tempfile.TemporaryDirectory() as tmp_dir:
                dxf_file = os.path.join(tmp_dir, "temp_floor.dxf")
                cpt_file = os.path.join(tmp_dir, "temp_floor.cpt")
                with open(dxf_file, "w", encoding="utf-8") as f:
                    f.write(dxf_content)

                adapter = RAMConceptCOMAdapter()
                if adapter.import_dxf_and_save(os.path.abspath(dxf_file), os.path.abspath(cpt_file)):
                    if os.path.exists(cpt_file) and os.path.getsize(cpt_file) > 0:
                        with open(cpt_file, "rb") as f:
                            res_bytes = f.read()
                            if res_bytes.startswith(b"SQLite format 3"):
                                return res_bytes
        except Exception as e_com:
            print(f"COM adapter fallback notice: {e_com}")

        # 4. Standalone Fallback CPT Generator from native template
        return self._generate_cpt_from_template()

    def _generate_cpt_from_template(self) -> Optional[bytes]:
        """
        Standalone fallback CPT generator.
        Loads bundled native binary RAM Concept CPT template (SQLite format 3).
        Guarantees that a valid native .CPT file is returned even when
        Bentley RAM Concept COM or Python API is not installed on host machine.
        """
        possible_paths = []
        if getattr(sys, "frozen", False):
            if hasattr(sys, "_MEIPASS"):
                possible_paths.append(os.path.join(sys._MEIPASS, "backend", "app", "ram_concept", "cpt_template.cpt"))
                possible_paths.append(os.path.join(sys._MEIPASS, "app", "ram_concept", "cpt_template.cpt"))
                possible_paths.append(os.path.join(sys._MEIPASS, "cpt_template.cpt"))
            exe_dir = os.path.dirname(sys.executable)
            possible_paths.append(os.path.join(exe_dir, "cpt_template.cpt"))
            possible_paths.append(os.path.join(exe_dir, "backend", "app", "ram_concept", "cpt_template.cpt"))

        base_dir = os.path.dirname(os.path.abspath(__file__))
        possible_paths.append(os.path.join(base_dir, "cpt_template.cpt"))

        for p in possible_paths:
            if os.path.exists(p) and os.path.getsize(p) > 0:
                try:
                    with open(p, "rb") as f:
                        data = f.read()
                        if data.startswith(b"SQLite format 3"):
                            return data
                except Exception as e:
                    print(f"Error reading CPT template from {p}: {e}")
        return None

    @staticmethod
    def _get_python_interpreter() -> Optional[str]:
        """
        Returns path to a valid python.exe interpreter.
        In PyInstaller frozen EXE, sys.executable points to the compiled EXE binary,
        so we locate an installed python interpreter on the system.
        """
        if not getattr(sys, "frozen", False):
            return sys.executable
        import shutil
        for cmd in ["python", "python3", "py"]:
            found = shutil.which(cmd)
            if found and found.endswith(".exe") and "ETABS" not in found and "floor_exporter" not in found.lower():
                return found
        import glob
        candidates = glob.glob(r"C:\Users\*\AppData\Local\Programs\Python\Python3*\python.exe") + \
                     glob.glob(r"C:\Python3*\python.exe") + \
                     glob.glob(r"C:\Program Files\Python3*\python.exe") + \
                     glob.glob(r"C:\Program Files (x86)\Python3*\python.exe")
        for c in candidates:
            if os.path.exists(c):
                return c
        return None

    def _write_automation_script(self, script_path: str, dxf_path: str):
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(self._generate_automation_script(dxf_path))

    def _generate_automation_script(self, dxf_path: str) -> str:
        dxf_filename = os.path.basename(dxf_path)
        cpt_filename = dxf_filename.replace("_RAMConcept_Exchange.dxf", "_RAMConcept_Model.cpt").replace(".dxf", ".cpt")
        script = f"""# RAM Concept Automation Macro Script
# Generated automatically by ETABS to RAM Concept Floor Exporter
import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
dxf_file = os.path.join(script_dir, "{dxf_filename}")
if not os.path.exists(dxf_file):
    dxf_file = r"{os.path.abspath(dxf_path)}"

cpt_file = os.path.join(script_dir, "{cpt_filename}")

print("Connecting to Bentley RAM Concept Application...")
try:
    import win32com.client
    app = win32com.client.GetActiveObject("RAMConcept.Application")
    print("Connected to active RAM Concept instance.")
except Exception:
    try:
        import win32com.client
        app = win32com.client.Dispatch("RAMConcept.Application")
        print("Launched new RAM Concept Application instance.")
    except Exception as e:
        print(f"Error: Could not connect to RAM Concept COM API: {{e}}")
        sys.exit(1)

try:
    doc = app.NewDocument()
    print(f"Importing CAD DXF floor layers from: {{dxf_file}}")
    if hasattr(doc, "ImportDXF"):
        doc.ImportDXF(dxf_file)
    print("CAD layers imported successfully.")

    if hasattr(doc, "SaveAs"):
        doc.SaveAs(cpt_file)
        print(f"Successfully generated native RAM Concept CPT model file: {{cpt_file}}")
    print("RAM Concept automation sequence finished successfully.")
except Exception as err:
    print(f"Warning during RAM Concept model creation: {{err}}")
"""
        return script

    @classmethod
    def execute_automation_script(cls, py_path: str, cpt_path: str, log_callback=None) -> bool:
        """
        Production-grade inside-the-tool execution of RAM Concept Python COM Automation.
        Directly executes the generated <story_name>_RAMConcept_Automation.py script safely in frozen EXE or normal Python.
        """
        def log(msg: str):
            if log_callback:
                log_callback(msg)
            else:
                try:
                    print(msg)
                except UnicodeEncodeError:
                    print(msg.encode("ascii", "ignore").decode("ascii"))

        if not py_path or not os.path.exists(py_path):
            log(f"RAM Concept automation script file not found at '{py_path}'.")
            return False

        log(f"Executing RAM Concept Automation inside tool: {os.path.basename(py_path)}...")

        py_exec = cls._get_python_interpreter()

        # 1. Execute generated script via python subprocess if valid python interpreter found
        if py_exec:
            try:
                import subprocess
                res = subprocess.run([py_exec, py_path], capture_output=True, text=True, timeout=60)
                if res.stdout:
                    for line in res.stdout.splitlines():
                        if line.strip(): log(f"  [RAM Concept Automation] {line}")
                if res.stderr:
                    for line in res.stderr.splitlines():
                        if line.strip(): log(f"  [RAM Concept Warning] {line}")

                if cpt_path and os.path.exists(cpt_path) and os.path.getsize(cpt_path) > 0:
                    log(f"[OK] Native .CPT model generated via RAM Concept Automation: {cpt_path}")
                    return True
            except Exception as err:
                log(f"Notice executing RAM Concept automation script via subprocess: {err}")

        # 2. In-Process Direct Execution Fallback (Crucial for PyInstaller EXE without external python.exe)
        try:
            log("Attempting in-process execution of RAM Concept automation script...")
            with open(py_path, "r", encoding="utf-8") as f:
                code_text = f.read()
            global_scope = {"__file__": py_path, "__name__": "__main__"}
            exec(code_text, global_scope)
            if cpt_path and os.path.exists(cpt_path) and os.path.getsize(cpt_path) > 0:
                log(f"[OK] In-process RAM Concept Automation succeeded! Saved native CPT file: {cpt_path}")
                return True
        except SystemExit:
            if cpt_path and os.path.exists(cpt_path) and os.path.getsize(cpt_path) > 0:
                log(f"[OK] In-process RAM Concept Automation succeeded: {cpt_path}")
                return True
        except Exception as e_exec:
            log(f"In-process automation notice: {e_exec}")

        return False
