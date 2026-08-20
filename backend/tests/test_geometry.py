import pytest
from app.geometry.processor import GeometryProcessor, UnitConverter
from app.models.intermediate import Point2D, Slab


def test_polygon_validation_valid():
    pts = [Point2D(x=0, y=0), Point2D(x=10, y=0), Point2D(x=10, y=10), Point2D(x=0, y=10)]
    res = GeometryProcessor.validate_polygon(pts)
    assert res["is_valid"] is True
    assert res["area"] == 100.0


def test_polygon_validation_self_intersecting():
    # Bow-tie polygon (self-crossing)
    pts = [Point2D(x=0, y=0), Point2D(x=10, y=10), Point2D(x=10, y=0), Point2D(x=0, y=10)]
    res = GeometryProcessor.validate_polygon(pts)
    assert res["is_valid"] is False
    assert res["self_intersects"] is True


def test_unit_conversions():
    assert UnitConverter.convert_length(1000.0, "mm", "m") == 1.0
    assert UnitConverter.convert_length(1.0, "m", "mm") == 1000.0
    assert round(UnitConverter.convert_force(1.0, "kip", "kN"), 2) == 4.45
