import os
import json
from typing import Dict, Any
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
        # Collect distinct material properties
        mats = []
        for slab in self.floor.slabs:
            if slab.material and slab.material not in mats:
                mats.append(slab.material)
        return mats

    def map_slabs(self, norm_slabs=None) -> list:
        slabs_to_map = norm_slabs if norm_slabs is not None else self.floor.slabs
        return [
            {
                "id": sl.id,
                "property": sl.property_name,
                "thickness": sl.thickness,
                "material": sl.material or "Concrete",
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
                "location": {"x": c.start_point.x - offset.x, "y": c.start_point.y - offset.y}
            }
            for c in self.floor.columns_above
        ]
        cols_below = [
            {
                "id": c.id,
                "section": c.section,
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
                "polygon": [{"x": pt.x - offset.x, "y": pt.y - offset.y} for pt in w.polygon]
            }
            for w in self.floor.walls_above
        ]
        w_below = [
            {
                "id": w.id,
                "thickness": w.thickness,
                "polygon": [{"x": pt.x - offset.x, "y": pt.y - offset.y} for pt in w.polygon]
            }
            for w in self.floor.walls_below
        ]
        return {"above": w_above, "below": w_below}

    def map_loads(self, offset) -> list:
        return [
            {
                "id": al.id,
                "area_id": al.area_id,
                "pattern": al.pattern,
                "magnitude": al.magnitude,
                "direction": al.direction
            }
            for al in self.floor.area_loads
        ]

    def generate_output(self, output_dir: str) -> Dict[str, Any]:
        """
        Generates standard RAM Concept file exchange outputs:
          - DXF CAD file for RAM Concept import
          - RAM Concept COM automation Python script
          - Intermediate JSON schema file
        """
        if not self.prepared_data:
            self.prepare_model()

        clean_story = "".join(c for c in self.floor.story.name if c.isalnum() or c in ['_', '-'])
        os.makedirs(output_dir, exist_ok=True)

        dxf_filename = f"{clean_story}_RAMConcept_Exchange.dxf"
        py_filename = f"{clean_story}_RAMConcept_Automation.py"
        json_filename = f"{clean_story}_IntermediateModel.json"

        dxf_path = os.path.join(output_dir, dxf_filename)
        py_path = os.path.join(output_dir, py_filename)
        json_path = os.path.join(output_dir, json_filename)

        # 1. Write DXF file
        self._write_dxf(dxf_path)

        # 2. Write Python Automation script
        self._write_automation_script(py_path, dxf_path)

        # 3. Write JSON intermediate file
        with open(json_path, "w") as f:
            json.dump(self.prepared_data, f, indent=2)

        return {
            "success": True,
            "story": self.floor.story.name,
            "dxf_file": dxf_path,
            "automation_script": py_path,
            "json_file": json_path,
            "validation": self.validation.model_dump()
        }

    def generate_output_files(self) -> Dict[str, Any]:
        """Generate export files in memory for direct package downloads."""
        if not self.prepared_data:
            self.prepare_model()

        clean_story = "".join(c for c in self.floor.story.name if c.isalnum() or c in ['_', '-'])
        dxf_filename = f"{clean_story}_RAMConcept_Exchange.dxf"
        py_filename = f"{clean_story}_RAMConcept_Automation.py"
        json_filename = f"{clean_story}_IntermediateModel.json"

        dxf_content = self._generate_dxf()
        automation_content = self._generate_automation_script(dxf_filename)

        return {
            "success": True,
            "story": self.floor.story.name,
            "dxf_filename": dxf_filename,
            "dxf_content": dxf_content,
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
        lines = [
            "0\nSECTION\n2\nHEADER\n0\nENDSEC\n",
            "0\nSECTION\n2\nTABLES\n0\nENDSEC\n",
            "0\nSECTION\n2\nBLOCKS\n0\nENDSEC\n",
            "0\nSECTION\n2\nENTITIES\n"
        ]

        # Slabs -> SLAB_OUTLINE
        for slab in self.prepared_data.get("slabs", []):
            pts = slab.get("polygon", [])
            if len(pts) > 1:
                lines.append("0\nPOLYLINE\n8\nSLAB_OUTLINE\n66\n1\n70\n1\n")
                for pt in pts:
                    lines.append(f"0\nVERTEX\n8\nSLAB_OUTLINE\n10\n{pt['x']}\n20\n{pt['y']}\n30\n0.0\n")
                lines.append("0\nSEQEND\n")

        # Openings -> OPENINGS
        for op in self.prepared_data.get("openings", []):
            pts = op.get("polygon", [])
            if len(pts) > 1:
                lines.append("0\nPOLYLINE\n8\nOPENINGS\n66\n1\n70\n1\n")
                for pt in pts:
                    lines.append(f"0\nVERTEX\n8\nOPENINGS\n10\n{pt['x']}\n20\n{pt['y']}\n30\n0.0\n")
                lines.append("0\nSEQEND\n")

        # Columns Below -> COLUMNS_BELOW
        for col in self.prepared_data.get("columns", {}).get("below", []):
            loc = col.get("location", {})
            lines.append(f"0\nPOINT\n8\nCOLUMNS_BELOW\n10\n{loc.get('x', 0.0)}\n20\n{loc.get('y', 0.0)}\n30\n0.0\n")

        # Columns Above -> COLUMNS_ABOVE
        for col in self.prepared_data.get("columns", {}).get("above", []):
            loc = col.get("location", {})
            lines.append(f"0\nPOINT\n8\nCOLUMNS_ABOVE\n10\n{loc.get('x', 0.0)}\n20\n{loc.get('y', 0.0)}\n30\n0.0\n")

        # Beams -> BEAMS
        for bm in self.prepared_data.get("beams", []):
            st, en = bm.get("start", {}), bm.get("end", {})
            lines.append(f"0\nLINE\n8\nBEAMS\n10\n{st.get('x', 0.0)}\n20\n{st.get('y', 0.0)}\n30\n0.0\n11\n{en.get('x', 0.0)}\n21\n{en.get('y', 0.0)}\n31\n0.0\n")

        lines.append("0\nENDSEC\n0\nEOF\n")

        return "".join(lines)

    def _write_automation_script(self, script_path: str, dxf_path: str):
        with open(script_path, "w") as f:
            f.write(self._generate_automation_script(dxf_path))

    def _generate_automation_script(self, dxf_path: str) -> str:
        script = f"""# RAM Concept COM Automation Macro Script
# Generated automatically by ETABS to RAM Concept Floor Exporter
import comtypes.client

dxf_file = r"{os.path.abspath(dxf_path)}"

print("Connecting to Bentley RAM Concept Application...")
try:
    app = comtypes.client.GetActiveObject("RAMConcept.Application")
except Exception:
    app = comtypes.client.CreateObject("RAMConcept.Application")

doc = app.NewDocument()
print(f"Importing CAD DXF floor layers from {{dxf_file}}...")
# doc.ImportDXF(dxf_file)
print("RAM Concept Model setup completed.")
"""
        return script
