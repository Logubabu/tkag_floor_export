import numpy as np
from shapely.geometry import Polygon, LineString, Point
from shapely.validation import make_valid
from typing import List, Tuple, Dict, Any, Optional
from app.models.intermediate import Point2D, Point3D, Slab


class UnitConverter:
    """
    Handles conversion between structural engineering unit systems.
    Internal standard: Length in meters (m), Force in Kilonewtons (kN).
    """
    LENGTH_TO_M = {
        "m": 1.0,
        "mm": 0.001,
        "in": 0.0254,
        "ft": 0.3048
    }

    FORCE_TO_KN = {
        "kn": 1.0,
        "n": 0.001,
        "kip": 4.44822,
        "lb": 0.00444822
    }

    @classmethod
    def convert_length(cls, val: float, from_unit: str, to_unit: str) -> float:
        from_u = from_unit.lower()
        to_u = to_unit.lower()
        if from_u not in cls.LENGTH_TO_M or to_u not in cls.LENGTH_TO_M:
            return val
        meters = val * cls.LENGTH_TO_M[from_u]
        return meters / cls.LENGTH_TO_M[to_u]

    @classmethod
    def convert_force(cls, val: float, from_unit: str, to_unit: str) -> float:
        from_u = from_unit.lower()
        to_u = to_unit.lower()
        if from_u not in cls.FORCE_TO_KN or to_u not in cls.FORCE_TO_KN:
            return val
        kn = val * cls.FORCE_TO_KN[from_u]
        return kn / cls.FORCE_TO_KN[to_u]


class GeometryProcessor:
    """
    Shapely computational geometry utility for structural floor polygons, openings, and element intersections.
    """
    @staticmethod
    def create_shapely_polygon(pts: List[Point2D]) -> Optional[Polygon]:
        if len(pts) < 3:
            return None
        coords = [(pt.x, pt.y) for pt in pts]
        if coords[0] != coords[-1]:
            coords.append(coords[0])
        return Polygon(coords)

    @staticmethod
    def validate_polygon(pts: List[Point2D]) -> Dict[str, Any]:
        poly = GeometryProcessor.create_shapely_polygon(pts)
        if poly is None:
            return {
                "is_valid": False,
                "is_simple": False,
                "area": 0.0,
                "error": "Polygon must contain at least 3 distinct non-collinear vertices."
            }

        if not poly.is_valid:
            try:
                poly = make_valid(poly)
                if poly.geom_type == 'MultiPolygon':
                    poly = max(poly.geoms, key=lambda g: g.area)
            except Exception:
                pass

        area = getattr(poly, 'area', 0.0)
        centroid = getattr(poly, 'centroid', None)

        return {
            "is_valid": area > 1e-4,
            "is_simple": True,
            "area": round(area, 4),
            "self_intersects": False,
            "centroid": (round(centroid.x, 3), round(centroid.y, 3)) if centroid else (0, 0)
        }

    @staticmethod
    def is_opening_inside_slab(opening_pts: List[Point2D], slab_pts: List[Point2D]) -> bool:
        op_poly = GeometryProcessor.create_shapely_polygon(opening_pts)
        sl_poly = GeometryProcessor.create_shapely_polygon(slab_pts)

        if op_poly is None or sl_poly is None:
            return False

        # Opening is inside slab if slab contains opening or intersects substantially
        return sl_poly.contains(op_poly) or sl_poly.intersects(op_poly)

    @staticmethod
    def normalize_coordinates(slabs: List[Slab]) -> Tuple[List[Slab], Point2D]:
        """
        Shifts all coordinates so the minimum bounding box origin starts at (0.0, 0.0).
        Returns normalized slabs and the applied offset vector.
        """
        min_x, min_y = float('inf'), float('inf')
        for slab in slabs:
            for pt in slab.polygon:
                if pt.x < min_x:
                    min_x = pt.x
                if pt.y < min_y:
                    min_y = pt.y

        if min_x == float('inf'):
            min_x, min_y = 0.0, 0.0

        offset = Point2D(x=min_x, y=min_y)
        normalized_slabs = []
        for slab in slabs:
            norm_pts = [Point2D(x=pt.x - min_x, y=pt.y - min_y) for pt in slab.polygon]
            norm_slab = slab.model_copy()
            norm_slab.polygon = norm_pts
            normalized_slabs.append(norm_slab)

        return normalized_slabs, offset
