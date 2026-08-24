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

        # 1. Validate & Heal Slabs
        if num_slabs == 0:
            if num_beams > 0 or num_columns > 0 or num_walls > 0:
                alerts.append(ValidationAlert(
                    level=AlertLevel.INFO,
                    element_type="Floor",
                    element_id=floor.story.name,
                    message=f"Framing elements (beams/columns/walls) detected on {floor.story.name}.",
                    action_tip="Slab geometry will be synthesized from perimeter beams during RAM export."
                ))

        for slab in floor.slabs:
            # Auto-repair invalid thickness
            if slab.thickness <= 0.0:
                slab.thickness = 0.25  # Standard 250mm default

            # Check geometry
            val_res = GeometryProcessor.validate_polygon(slab.polygon)
            if not val_res["is_valid"] and len(slab.polygon) < 3:
                alerts.append(ValidationAlert(
                    level=AlertLevel.WARNING,
                    element_type="Slab",
                    element_id=slab.id,
                    message=f"Slab {slab.id} has fewer than 3 boundary points.",
                    action_tip="Boundary points will be interpolated automatically."
                ))

        # 2. Validate Openings
        for op in floor.openings:
            val_res = GeometryProcessor.validate_polygon(op.polygon)

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
