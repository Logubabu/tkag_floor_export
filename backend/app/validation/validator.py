from typing import List, Dict, Any
from app.models.intermediate import (
    FloorModel, ValidationResult, ValidationAlert, AlertLevel, Slab
)
from app.geometry.processor import GeometryProcessor


class StructuralValidator:
    """
    Structural Engineering Validation Engine.
    Validates geometric integrity, material properties, section attributes,
    and boundary conditions prior to RAM Concept model generation.
    """
    @staticmethod
    def validate_floor(floor: FloorModel) -> ValidationResult:
        alerts: List[ValidationAlert] = []
        
        num_slabs = len(floor.slabs)
        num_openings = len(floor.openings)
        num_beams = len(floor.beams)
        num_columns = len(floor.columns_above) + len(floor.columns_below)
        num_walls = len(floor.walls_above) + len(floor.walls_below)

        # 1. Validate Slabs
        if num_slabs == 0:
            alerts.append(ValidationAlert(
                level=AlertLevel.ERROR,
                element_type="Floor",
                element_id=floor.story.name,
                message=f"No structural slabs found on {floor.story.name}.",
                action_tip="Verify story assignment in ETABS or select a different extraction mode."
            ))

        for slab in floor.slabs:
            # Check thickness
            if slab.thickness <= 0.0:
                alerts.append(ValidationAlert(
                    level=AlertLevel.ERROR,
                    element_type="Slab",
                    element_id=slab.id,
                    message=f"Slab {slab.id} has invalid or zero thickness ({slab.thickness} m).",
                    action_tip="Assign a valid slab thickness (> 0.0 mm) in ETABS section properties."
                ))

            # Check geometry & self-intersection
            val_res = GeometryProcessor.validate_polygon(slab.polygon)
            if not val_res["is_valid"]:
                if val_res.get("self_intersects"):
                    alerts.append(ValidationAlert(
                        level=AlertLevel.ERROR,
                        element_type="Slab",
                        element_id=slab.id,
                        message=f"Slab {slab.id} polygon has self-intersecting edges.",
                        action_tip="Clean up self-crossing vertices in ETABS model geometry."
                    ))
                else:
                    alerts.append(ValidationAlert(
                        level=AlertLevel.ERROR,
                        element_type="Slab",
                        element_id=slab.id,
                        message=f"Slab {slab.id} has invalid geometry ({val_res.get('error', 'Degenerate polygon')}).",
                        action_tip="Ensure slab boundary forms a closed simple polygon with at least 3 points."
                    ))

        # 2. Validate Openings
        for op in floor.openings:
            val_res = GeometryProcessor.validate_polygon(op.polygon)
            if not val_res["is_valid"]:
                alerts.append(ValidationAlert(
                    level=AlertLevel.WARNING,
                    element_type="Opening",
                    element_id=op.id,
                    message=f"Opening {op.id} has invalid perimeter geometry.",
                    action_tip="Verify opening boundary vertices in ETABS model."
                ))

        # 3. Check for orphan support warnings
        if num_columns == 0 and num_walls == 0:
            alerts.append(ValidationAlert(
                level=AlertLevel.WARNING,
                element_type="FloorSupport",
                element_id=floor.story.name,
                message=f"No vertical supports (columns/walls) detected on {floor.story.name}.",
                action_tip="Check if story mode B or C should be selected to include lower story supports."
            ))

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
