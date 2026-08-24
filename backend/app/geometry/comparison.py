from typing import Dict, Any, List, Optional
import math
from app.models.intermediate import FloorModel, Slab, Frame, Wall
from app.geometry.processor import GeometryProcessor, UnitConverter

class GeometryComparisonEngine:
    """
    Computes visual and structural geometry comparison metrics between
    source ETABS floor model and generated RAM Concept floor model.
    """

    @staticmethod
    def calculate_floor_metrics(model: FloorModel) -> Dict[str, Any]:
        total_slab_area = 0.0
        total_opening_area = 0.0
        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = float('-inf'), float('-inf')

        weighted_cx_sum = 0.0
        weighted_cy_sum = 0.0

        for slab in model.slabs:
            res = GeometryProcessor.validate_polygon(slab.polygon)
            area = res.get("area", 0.0)
            total_slab_area += area
            cx, cy = res.get("centroid", (0.0, 0.0))
            weighted_cx_sum += cx * area
            weighted_cy_sum += cy * area

            for pt in slab.polygon:
                min_x = min(min_x, pt.x)
                min_y = min(min_y, pt.y)
                max_x = max(max_x, pt.x)
                max_y = max(max_y, pt.y)

        for op in model.openings:
            res = GeometryProcessor.validate_polygon(op.polygon)
            total_opening_area += res.get("area", 0.0)

        net_area = max(0.0, total_slab_area - total_opening_area)
        centroid_x = round(weighted_cx_sum / total_slab_area, 3) if total_slab_area > 0 else 0.0
        centroid_y = round(weighted_cy_sum / total_slab_area, 3) if total_slab_area > 0 else 0.0

        if min_x == float('inf'):
            min_x, min_y, max_x, max_y = 0.0, 0.0, 0.0, 0.0

        return {
            "slabs_count": len(model.slabs),
            "openings_count": len(model.openings),
            "columns_count": len(model.columns_above) + len(model.columns_below),
            "walls_count": len(model.walls_above) + len(model.walls_below),
            "beams_count": len(model.beams),
            "gross_slab_area": round(total_slab_area, 2),
            "opening_area": round(total_opening_area, 2),
            "net_slab_area": round(net_area, 2),
            "bounding_box": {
                "min_x": round(min_x, 3),
                "min_y": round(min_y, 3),
                "max_x": round(max_x, 3),
                "max_y": round(max_y, 3),
                "width": round(max_x - min_x, 3),
                "height": round(max_y - min_y, 3)
            },
            "centroid": {"x": centroid_x, "y": centroid_y}
        }

    @classmethod
    def compare_models(cls, source_model: FloorModel, target_model: FloorModel, tolerance_mm: float = 1.0) -> Dict[str, Any]:
        source_m = cls.calculate_floor_metrics(source_model)
        target_m = cls.calculate_floor_metrics(target_model)

        area_diff = abs(source_m["net_slab_area"] - target_m["net_slab_area"])
        centroid_dist = math.sqrt(
            (source_m["centroid"]["x"] - target_m["centroid"]["x"]) ** 2 +
            (source_m["centroid"]["y"] - target_m["centroid"]["y"]) ** 2
        )

        match_status = "PERFECT_MATCH"
        if area_diff > 0.01 or centroid_dist > (tolerance_mm / 1000.0):
            match_status = "WARNING_DEVIATION"
        if source_m["slabs_count"] != target_m["slabs_count"] or source_m["openings_count"] != target_m["openings_count"]:
            match_status = "ELEMENT_MISMATCH"

        return {
            "status": match_status,
            "tolerance_mm": tolerance_mm,
            "source_metrics": source_m,
            "target_metrics": target_m,
            "deviations": {
                "net_area_diff_m2": round(area_diff, 4),
                "centroid_distance_m": round(centroid_dist, 4),
                "missing_slabs": source_m["slabs_count"] - target_m["slabs_count"],
                "missing_openings": source_m["openings_count"] - target_m["openings_count"],
                "missing_columns": source_m["columns_count"] - target_m["columns_count"],
                "missing_walls": source_m["walls_count"] - target_m["walls_count"]
            }
        }
