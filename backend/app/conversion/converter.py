"""
Conversion Engine.
Maps ETABS normalized objects to RAM Concept structural entities with status tracking.
"""
from typing import Dict, Any, List
from shapely.geometry import Polygon
from app.models.intermediate import StructuralModel

class ConversionRecord:
    def __init__(self, etabs_id: str, etabs_type: str, status: str = "SUCCESS", details: str = ""):
        self.etabs_id = etabs_id
        self.etabs_type = etabs_type
        self.status = status  # SUCCESS, WARNING, MANUAL_REVIEW_REQUIRED, FAILED
        self.details = details

class ModelConverter:
    """Converts normalized structural model into RAM Concept target structures."""

    def __init__(self):
        self.records: List[ConversionRecord] = []

    def convert(self, model: StructuralModel) -> StructuralModel:
        """
        Converts and sanitizes model geometry and mapping records.
        """
        self.records.clear()
        
        # 1. Process Slabs
        sanitized_slabs = []
        for slab in model.slabs:
            rec = ConversionRecord(slab.id, "Slab")
            if len(slab.points) < 3:
                rec.status = "FAILED"
                rec.details = "Slab polygon has less than 3 points."
                self.records.append(rec)
                continue
                
            poly = Polygon(slab.points)
            if not poly.is_valid or poly.area == 0:
                rec.status = "WARNING"
                rec.details = "Invalid or zero-area polygon; sanitized via buffer."
                poly = poly.buffer(0)
                
            # Ensure counter-clockwise (CCW) winding
            if poly.is_valid and not poly.exterior.is_ccw:
                slab.points = list(reversed(slab.points))
                rec.details += " Polygon orientation converted to CCW."
                
            sanitized_slabs.append(slab)
            self.records.append(rec)

        # 2. Process Walls
        for wall in model.walls:
            rec = ConversionRecord(wall.id, "Wall")
            if wall.p1 == wall.p2:
                rec.status = "FAILED"
                rec.details = "Wall has zero length."
            self.records.append(rec)

        # 3. Process Columns
        for col in model.columns:
            rec = ConversionRecord(col.id, "Column")
            self.records.append(rec)

        # 4. Process Beams
        for beam in model.beams:
            rec = ConversionRecord(beam.id, "Beam")
            if beam.p1 == beam.p2:
                rec.status = "FAILED"
                rec.details = "Beam has zero length."
            self.records.append(rec)

        # 5. Process Openings
        for op in model.openings:
            rec = ConversionRecord(op.id, "Opening")
            if len(op.points) < 3:
                rec.status = "FAILED"
                rec.details = "Opening polygon has less than 3 points."
            self.records.append(rec)

        return model

    def get_summary(self) -> Dict[str, int]:
        counts = {"SUCCESS": 0, "WARNING": 0, "MANUAL_REVIEW_REQUIRED": 0, "FAILED": 0}
        for r in self.records:
            counts[r.status] = counts.get(r.status, 0) + 1
        return counts
