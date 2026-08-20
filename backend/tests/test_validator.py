import pytest
from app.models.intermediate import FloorModel, Story, Slab, Point2D
from app.validation.validator import StructuralValidator


def test_validator_detects_invalid_thickness():
    story = Story(id="s1", name="Level 1", elevation=3.0, height=3.0)
    invalid_slab = Slab(
        id="S1",
        story="Level 1",
        polygon=[Point2D(x=0, y=0), Point2D(x=5, y=0), Point2D(x=5, y=5), Point2D(x=0, y=5)],
        thickness=0.0
    )
    floor = FloorModel(story=story, slabs=[invalid_slab])
    res = StructuralValidator.validate_floor(floor)
    
    assert res.is_valid is False
    assert any("thickness" in a.message.lower() for a in res.alerts)
