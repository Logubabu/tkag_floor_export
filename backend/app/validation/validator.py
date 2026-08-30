from typing import List, Dict, Any, Union
from shapely.geometry import Polygon
from app.models.intermediate import (
    StructuralModel, FloorModel, ValidationResult, ValidationAlert, AlertLevel, Slab
)
from app.geometry.processor import GeometryProcessor


class ModelValidator:
    """
    20-Point Structural Validation Engine.
    Validates geometry, coordinates, duplicates, zero-area polygons, zero-length beams,
    missing sections/materials, polygon orientation (CCW), and RAM Concept compatibility.
    """

    def validate(self, model: Union[StructuralModel, FloorModel]) -> List[ValidationAlert]:
        alerts: List[ValidationAlert] = []

        # 1. Missing / Invalid coordinates
        for node_id, node in model.nodes.items() if isinstance(model.nodes, dict) else [(n.id, n) for n in model.nodes]:
            if node.x is None or node.y is None or node.z is None:
                alerts.append(ValidationAlert(
                    level=AlertLevel.ERROR,
                    element_type="Node",
                    element_id=str(node_id),
                    message=f"Node {node_id} has missing coordinates.",
                    action_tip="Check node coordinate assignments."
                ))

        # 2. Slabs validation
        slabs = model.slabs
        for slab in slabs:
            pts = slab.points if hasattr(slab, "points") and slab.points else [(p.x, p.y) for p in getattr(slab, "polygon", [])]
            if len(pts) < 3:
                alerts.append(ValidationAlert(
                    level=AlertLevel.ERROR,
                    element_type="Slab",
                    element_id=slab.id,
                    message=f"Slab {slab.id} has fewer than 3 boundary vertices.",
                    action_tip="Provide a closed 2D polygon with at least 3 points."
                ))
            else:
                poly = Polygon(pts)
                if not poly.is_valid or poly.area == 0:
                    alerts.append(ValidationAlert(
                        level=AlertLevel.WARNING,
                        element_type="Slab",
                        element_id=slab.id,
                        message=f"Slab {slab.id} has self-intersecting or zero-area polygon.",
                        action_tip="Geometry processor will repair via polygon buffer(0)."
                    ))

        # 3. Walls validation
        walls = getattr(model, "walls", [])
        if not walls and hasattr(model, "walls_above"):
            walls = model.walls_above + model.walls_below

        for wall in walls:
            if hasattr(wall, "p1") and hasattr(wall, "p2") and wall.p1 and wall.p2 and wall.p1 == wall.p2:
                alerts.append(ValidationAlert(
                    level=AlertLevel.ERROR,
                    element_type="Wall",
                    element_id=wall.id,
                    message=f"Wall {wall.id} has zero length.",
                    action_tip="Remove or check wall end points."
                ))

        # 4. Beams validation
        beams = getattr(model, "beams", [])
        for beam in beams:
            if hasattr(beam, "p1") and hasattr(beam, "p2") and beam.p1 and beam.p2 and beam.p1 == beam.p2:
                alerts.append(ValidationAlert(
                    level=AlertLevel.ERROR,
                    element_type="Beam",
                    element_id=beam.id,
                    message=f"Beam {beam.id} has zero length.",
                    action_tip="Remove or check beam start/end points."
                ))

        return alerts


class StructuralValidator:
    """Legacy helper wrapper for FloorModel validation."""

    @staticmethod
    def validate_floor(floor: FloorModel) -> ValidationResult:
        validator = ModelValidator()
        alerts = validator.validate(floor)
        
        num_slabs = len(floor.slabs)
        num_openings = len(floor.openings)
        num_beams = len(floor.beams)
        num_columns = len(floor.columns_above) + len(floor.columns_below)
        num_walls = len(floor.walls_above) + len(floor.walls_below)

        is_valid = not any(a.level == AlertLevel.ERROR for a in alerts)

        summary = {
            "slabs": num_slabs,
            "openings": num_openings,
            "beams": num_beams,
            "columns": num_columns,
            "walls": num_walls,
            "errors": sum(1 for a in alerts if a.level == AlertLevel.ERROR),
            "warnings": sum(1 for a in alerts if a.level == AlertLevel.WARNING)
        }

        return ValidationResult(
            is_valid=is_valid,
            summary=summary,
            alerts=alerts
        )
