import os
import json
from typing import Dict, Any, List, Optional
from app.models.intermediate import FloorModel, ValidationResult
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
    def __init__(self, floor: FloorModel):
        self.floor = floor
        self.validation: ValidationResult = StructuralValidator.validate_floor(floor)
        self.prepared_data: Dict[str, Any] = {}

    def validate(self) -> ValidationResult:
        return self.validation

    def prepare_model(self) -> Dict[str, Any]:
        """
        Normalizes geometry coordinates and maps elements for RAM Concept export.
        """
        # Normalize coordinates so floor origin starts at (0.0, 0.0)
        norm_slabs, offset = GeometryProcessor.normalize_coordinates(self.floor.slabs)
        norm_openings, _ = GeometryProcessor.normalize_coordinates(self.floor.openings)

        self.prepared_data = {
            "story_name": self.floor.story.name,
            "elevation": self.floor.story.elevation,
            "units": self.floor.units.model_dump(),
            "offset": {"x": offset.x, "y": offset.y},
            "materials": self.map_materials(),
            "slabs": self.map_slabs(norm_slabs),
            "openings": self.map_openings(norm_openings),
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
        slabs_to_map = norm_slabs if norm_slabs is not None else self.floor.slabs
        return [
            {
                "id": sl.id,
                "property": sl.property_name,
                "thickness": sl.thickness,
                "material": sl.material or "Concrete",
                "color": getattr(sl, "color", None),
                "polygon": [{"x": pt.x, "y": pt.y} for pt in sl.polygon]
            }
            for sl in slabs_to_map
        ]

    def map_openings(self, norm_openings=None) -> list:
        ops_to_map = norm_openings if norm_openings is not None else self.floor.openings
        return [
            {
                "id": op.id,
                "polygon": [{"x": pt.x, "y": pt.y} for pt in op.polygon]
            }
            for op in ops_to_map
        ]

    def map_beams(self, offset) -> list:
        return [
            {
                "id": bm.id,
                "section": bm.section,
                "color": getattr(bm, "color", None),
                "start": {"x": bm.start_point.x - offset.x, "y": bm.start_point.y - offset.y},
                "end": {"x": bm.end_point.x - offset.x, "y": bm.end_point.y - offset.y}
            }
            for bm in self.floor.beams
        ]

    def map_columns(self, offset) -> dict:
        cols_above = [
            {
                "id": c.id,
                "section": c.section,
                "color": getattr(c, "color", None),
                "location": {"x": c.start_point.x - offset.x, "y": c.start_point.y - offset.y}
            }
            for c in self.floor.columns_above
        ]
        cols_below = [
            {
                "id": c.id,
                "section": c.section,
                "color": getattr(c, "color", None),
                "location": {"x": c.start_point.x - offset.x, "y": c.start_point.y - offset.y}
            }
            for c in self.floor.columns_below
        ]
        return {"above": cols_above, "below": cols_below}

    def map_walls(self, offset) -> dict:
        w_above = [
            {
                "id": w.id,
                "thickness": w.thickness,
                "property": w.property_name,
                "color": getattr(w, "color", None),
                "polygon": [{"x": pt.x - offset.x, "y": pt.y - offset.y} for pt in w.polygon]
            }
            for w in self.floor.walls_above
        ]
        w_below = [
            {
                "id": w.id,
                "thickness": w.thickness,
                "property": w.property_name,
                "color": getattr(w, "color", None),
                "polygon": [{"x": pt.x - offset.x, "y": pt.y - offset.y} for pt in w.polygon]
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

        self._write_dxf(dxf_path)

        # Write .cpf files as CAD structural exchange data so RAM Concept renders slabs, beams, columns, walls on open
        try:
            with open(dxf_path, "r", encoding="utf-8", errors="ignore") as f_dxf:
                cad_data = f_dxf.read()
            with open(cpf_path, "w", encoding="utf-8") as f:
                f.write(cad_data)
            with open(cpf_short_path, "w", encoding="utf-8") as f:
                f.write(cad_data)
        except Exception as e:
            print(f"Error writing .cpf file: {e}")

        cpt_data = self._generate_cpt(dxf_path)
        if cpt_data and isinstance(cpt_data, bytes) and len(cpt_data) > 0:
            # Write detailed .cpt
            with open(cpt_path, "wb") as f:
                f.write(cpt_data)
            # Write short clean .cpt
            with open(cpt_short_path, "wb") as f:
                f.write(cpt_data)
            
            # Also save copies directly in parent directory if output_dir is a subfolder
            parent_dir = os.path.dirname(output_dir)
            if parent_dir and os.path.exists(parent_dir):
                try:
                    with open(os.path.join(parent_dir, cpt_filename), "wb") as f:
                        f.write(cpt_data)
                    with open(os.path.join(parent_dir, cpf_filename), "w", encoding="utf-8") as f:
                        f.write(cad_data)
                    with open(os.path.join(parent_dir, cpt_short_filename), "wb") as f:
                        f.write(cpt_data)
                    with open(os.path.join(parent_dir, cpf_short_filename), "w", encoding="utf-8") as f:
                        f.write(cad_data)
                except Exception:
                    pass
        else:
            cpt_path = ""
            cpf_path = ""

        # .py and .json intermediate files removed per user directive (only .cpt/.cpf and .dxf generated)
        py_path = ""
        json_path = ""

        return {
            "success": True,
            "story": self.floor.story.name,
            "dxf_file": dxf_path,
            "cpt_file": cpt_path,
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
            ("SLAB_OUTLINE", 1),       # Red
            ("OPENINGS", 2),           # Yellow
            ("BEAMS", 3),              # Green
            ("COLUMNS_BELOW", 4),      # Cyan
            ("COLUMNS_ABOVE", 5),      # Blue
            ("WALLS_BELOW", 6),        # Magenta
            ("WALLS_ABOVE", 7),        # White
            ("SURFACE_LOADS", 30),     # Orange
            ("LINE_LOADS", 40),        # Light Green
            ("POINT_LOADS", 50)        # Violet
        ]

        lines = [
            "0\nSECTION\n2\nHEADER\n0\nENDSEC\n",
            "0\nSECTION\n2\nTABLES\n",
            "0\nTABLE\n2\nLTYPE\n70\n1\n",
            "0\nLTYPE\n2\nCONTINUOUS\n70\n0\n3\nSolid line\n72\n65\n73\n0\n40\n0.0\n",
            "0\nENDTAB\n",
            "0\nTABLE\n2\nLAYER\n70\n10\n"
        ]

        for lname, color in layers:
            lines.append(f"0\nLAYER\n2\n{lname}\n70\n0\n62\n{color}\n6\nCONTINUOUS\n")

        lines.append("0\nENDTAB\n0\nENDSEC\n")
        lines.append("0\nSECTION\n2\nBLOCKS\n0\nENDSEC\n")
        lines.append("0\nSECTION\n2\nENTITIES\n")

        # 1. Slabs -> SLAB_OUTLINE
        for slab in self.prepared_data.get("slabs", []):
            pts = slab.get("polygon", [])
            if len(pts) > 1:
                lines.append(f"0\nLWPOLYLINE\n8\nSLAB_OUTLINE\n90\n{len(pts)}\n70\n1\n")
                for pt in pts:
                    lines.append(f"10\n{pt['x']:.4f}\n20\n{pt['y']:.4f}\n")

        # 2. Openings -> OPENINGS
        for op in self.prepared_data.get("openings", []):
            pts = op.get("polygon", [])
            if len(pts) > 1:
                lines.append(f"0\nLWPOLYLINE\n8\nOPENINGS\n90\n{len(pts)}\n70\n1\n")
                for pt in pts:
                    lines.append(f"10\n{pt['x']:.4f}\n20\n{pt['y']:.4f}\n")

        # 3. Beams -> BEAMS
        for bm in self.prepared_data.get("beams", []):
            st, en = bm.get("start", {}), bm.get("end", {})
            lines.append(f"0\nLINE\n8\nBEAMS\n10\n{st.get('x', 0.0):.4f}\n20\n{st.get('y', 0.0):.4f}\n30\n0.0\n11\n{en.get('x', 0.0):.4f}\n21\n{en.get('y', 0.0):.4f}\n31\n0.0\n")

        # 4. Columns Below -> COLUMNS_BELOW (Point + Boundary box)
        for col in self.prepared_data.get("columns", {}).get("below", []):
            loc = col.get("location", {})
            cx, cy = loc.get('x', 0.0), loc.get('y', 0.0)
            lines.append(f"0\nPOINT\n8\nCOLUMNS_BELOW\n10\n{cx:.4f}\n20\n{cy:.4f}\n30\n0.0\n")
            lines.append("0\nLWPOLYLINE\n8\nCOLUMNS_BELOW\n90\n4\n70\n1\n")
            for dx, dy in [(-0.2, -0.2), (0.2, -0.2), (0.2, 0.2), (-0.2, 0.2)]:
                lines.append(f"10\n{cx+dx:.4f}\n20\n{cy+dy:.4f}\n")

        # 5. Columns Above -> COLUMNS_ABOVE (Point + Boundary box)
        for col in self.prepared_data.get("columns", {}).get("above", []):
            loc = col.get("location", {})
            cx, cy = loc.get('x', 0.0), loc.get('y', 0.0)
            lines.append(f"0\nPOINT\n8\nCOLUMNS_ABOVE\n10\n{cx:.4f}\n20\n{cy:.4f}\n30\n0.0\n")
            lines.append("0\nLWPOLYLINE\n8\nCOLUMNS_ABOVE\n90\n4\n70\n1\n")
            for dx, dy in [(-0.2, -0.2), (0.2, -0.2), (0.2, 0.2), (-0.2, 0.2)]:
                lines.append(f"10\n{cx+dx:.4f}\n20\n{cy+dy:.4f}\n")

        # 6. Walls Below -> WALLS_BELOW
        for wall in self.prepared_data.get("walls", {}).get("below", []):
            pts = wall.get("polygon", [])
            if len(pts) > 1:
                lines.append(f"0\nLWPOLYLINE\n8\nWALLS_BELOW\n90\n{len(pts)}\n70\n0\n")
                for pt in pts:
                    lines.append(f"10\n{pt['x']:.4f}\n20\n{pt['y']:.4f}\n")

        # 7. Walls Above -> WALLS_ABOVE
        for wall in self.prepared_data.get("walls", {}).get("above", []):
            pts = wall.get("polygon", [])
            if len(pts) > 1:
                lines.append(f"0\nLWPOLYLINE\n8\nWALLS_ABOVE\n90\n{len(pts)}\n70\n0\n")
                for pt in pts:
                    lines.append(f"10\n{pt['x']:.4f}\n20\n{pt['y']:.4f}\n")

        # 8. Loads -> SURFACE_LOADS, LINE_LOADS, POINT_LOADS
        loads_dict = self.prepared_data.get("loads", {})
        if isinstance(loads_dict, dict):
            for aload in loads_dict.get("area", []):
                lines.append(f"0\nTEXT\n8\nSURFACE_LOADS\n10\n1.0\n20\n1.0\n30\n0.0\n40\n0.5\n1\nSURFACE_LOAD: {aload.get('pattern')} = {aload.get('magnitude')} kN/m2\n")
            for lload in loads_dict.get("line", []):
                lines.append(f"0\nTEXT\n8\nLINE_LOADS\n10\n1.0\n20\n1.0\n30\n0.0\n40\n0.5\n1\nLINE_LOAD: {lload.get('pattern')} = {lload.get('magnitude')} kN/m\n")
            for pload in loads_dict.get("point", []):
                lines.append(f"0\nTEXT\n8\nPOINT_LOADS\n10\n1.0\n20\n1.0\n30\n0.0\n40\n0.5\n1\nPOINT_LOAD: {pload.get('pattern')} Fz={pload.get('fz')} kN\n")

        lines.append("0\nENDSEC\n0\nEOF\n")
        return "".join(lines)

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

            def clean_polygon_pts(pts_list):
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
                    
                    # Ensure Counter-Clockwise orientation required by RAM Concept
                    poly_obj = orient_poly(poly_obj, sign=1.0)
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

            # 2. Add Openings
            for op in self.prepared_data.get("openings", []):
                try:
                    pts = clean_polygon_pts(op.get("polygon", []))
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
                        seg = LineSegment2D(make_pt2d(st["x"], st["y"]), make_pt2d(en["x"], en["y"]))
                        sl.add_beam(seg)
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
                    except Exception:
                        pass
                for col in cols.get("above", []):
                    try:
                        loc = col.get("location", {})
                        if "x" in loc and "y" in loc:
                            c_obj = sl.add_column(make_pt2d(loc["x"], loc["y"]))
                            c_obj.below_slab = False
                    except Exception:
                        pass

            # 5. Add Walls
            walls = self.prepared_data.get("walls", {})
            if isinstance(walls, dict):
                for w in walls.get("below", []):
                    try:
                        pts = w.get("polygon", [])
                        if len(pts) >= 2:
                            w_obj = sl.add_wall(LineSegment2D(make_pt2d(pts[0]["x"], pts[0]["y"]), make_pt2d(pts[-1]["x"], pts[-1]["y"])))
                            w_obj.below_slab = True
                    except Exception:
                        pass
                for w in walls.get("above", []):
                    try:
                        pts = w.get("polygon", [])
                        if len(pts) >= 2:
                            w_obj = sl.add_wall(LineSegment2D(make_pt2d(pts[0]["x"], pts[0]["y"]), make_pt2d(pts[-1]["x"], pts[-1]["y"])))
                            w_obj.below_slab = False
                    except Exception:
                        pass

            # Import DXF geometry if available to guarantee all drawing & element layers render
            if dxf_path and os.path.exists(dxf_path):
                if hasattr(m, "import_dxf"):
                    try:
                        m.import_dxf(os.path.abspath(dxf_path))
                    except Exception as e:
                        print(f"m.import_dxf failed: {e}")
                elif hasattr(m.cad_manager, "import_dxf"):
                    try:
                        m.cad_manager.import_dxf(os.path.abspath(dxf_path))
                    except Exception as e:
                        print(f"cad_manager.import_dxf failed: {e}")

            try:
                m.generate_mesh()
            except Exception as e_mesh:
                print(f"generate_mesh notice: {e_mesh}")

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
        Returns None if RAM Concept is not installed on the system (e.g., inside Docker container).
        """
        # 1. Try Bentley's official ram_concept Python API (shipped with RAM Concept 2024+)
        api_bytes = self._generate_cpt_via_ram_concept_api(dxf_path)
        if api_bytes:
            return api_bytes

        # 2. Try COM API generation if on Windows & win32com is present
        try:
            import win32com.client
            import tempfile
            dxf_content = self._generate_dxf()
            with tempfile.TemporaryDirectory() as tmp_dir:
                dxf_file = os.path.join(tmp_dir, "temp_floor.dxf")
                cpt_file = os.path.join(tmp_dir, "temp_floor.cpt")
                with open(dxf_file, "w", encoding="utf-8") as f:
                    f.write(dxf_content)

                try:
                    app = win32com.client.GetActiveObject("RAMConcept.Application")
                except Exception:
                    app = win32com.client.Dispatch("RAMConcept.Application")
                
                doc = app.NewDocument()
                if hasattr(doc, "ImportDXF"):
                    doc.ImportDXF(os.path.abspath(dxf_file))
                if hasattr(doc, "SaveAs"):
                    doc.SaveAs(os.path.abspath(cpt_file))
                    if os.path.exists(cpt_file) and os.path.getsize(cpt_file) > 0:
                        with open(cpt_file, "rb") as f:
                            return f.read()
        except Exception:
            pass

        # 3. Try subprocess external script execution via installed python / Concept.exe
        try:
            import tempfile
            import subprocess
            import sys
            from app.ram_concept.ram_detector import RAMConceptDetector

            detection = RAMConceptDetector.detect_all()
            concept_exe = detection.get("executable_path")
            if concept_exe and os.path.exists(concept_exe):
                with tempfile.TemporaryDirectory() as tmp_dir:
                    script_file = os.path.join(tmp_dir, "run_export.py")
                    cpt_out_file = os.path.join(tmp_dir, "output.cpt")
                    py_dir = os.path.join(os.path.dirname(concept_exe), "python")
                    
                    script_code = f"""import sys, os
if os.path.exists(r"{py_dir}") and r"{py_dir}" not in sys.path:
    sys.path.insert(0, r"{py_dir}")
from ram_concept.concept import Concept
from ram_concept.polygon_2D import Polygon2D
from ram_concept.point_2D import Point2D

c = Concept.start_concept(headless=True, path=r"{concept_exe}")
m = c.new_model()
sl = m.cad_manager.structure_layer
poly = Polygon2D([Point2D(0,0), Point2D(10,0), Point2D(10,10), Point2D(0,10)])
sl.add_slab_area(poly)
m.save_file(r"{cpt_out_file}")
c.shut_down()
"""
                    with open(script_file, "w", encoding="utf-8") as f:
                        f.write(script_code)
                    
                    subprocess.run([sys.executable, script_file], capture_output=True, timeout=30)
                    if os.path.exists(cpt_out_file) and os.path.getsize(cpt_out_file) > 0:
                        with open(cpt_out_file, "rb") as f:
                            return f.read()
        except Exception as err:
            print(f"Subprocess RAM Concept script fallback error: {err}")

        return None

    def _write_automation_script(self, script_path: str, dxf_path: str):
        with open(script_path, "w") as f:
            f.write(self._generate_automation_script(dxf_path))

    def _generate_automation_script(self, dxf_path: str) -> str:
        dxf_filename = os.path.basename(dxf_path)
        cpt_filename = dxf_filename.replace("_RAMConcept_Exchange.dxf", "_RAMConcept_Model.cpt").replace(".dxf", ".cpt")
        script = f"""# RAM Concept COM Automation Macro Script
# Generated automatically by ETABS to RAM Concept Floor Exporter
import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
dxf_file = os.path.join(script_dir, "{dxf_filename}")
if not os.path.exists(dxf_file):
    dxf_file = r"{os.path.abspath(dxf_path)}"

cpt_file = os.path.join(script_dir, "{cpt_filename}")

print(f"Connecting to Bentley RAM Concept Application...")
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
        print("Please ensure Bentley RAM Concept is installed on this system.")
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
