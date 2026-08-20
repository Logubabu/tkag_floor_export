import os
import pytest
from app.etabs.e2k_parser import E2KParser
from app.floor_extractor.extractor import FloorExtractor
from app.models.intermediate import ExtractionMode


def test_floor_extraction_modes():
    sample_path = os.path.join(os.path.dirname(__file__), "..", "..", "sample_models", "sample_building.e2k")
    with open(sample_path, "r") as f:
        model = E2KParser().parse_string(f.read())

    # Test Mode A: Slab Only
    floor_a = FloorExtractor.extract_floor(model, "Level 5", ExtractionMode.SLAB_ONLY)
    assert floor_a.story.name == "Level 5"
    assert len(floor_a.slabs) > 0
    assert len(floor_a.columns_below) == 0

    # Test Mode B: Slab + Supporting Elements
    floor_b = FloorExtractor.extract_floor(model, "Level 5", ExtractionMode.SLAB_AND_SUPPORTS)
    assert len(floor_b.slabs) > 0
    assert len(floor_b.columns_below) > 0 or len(floor_b.beams) > 0
