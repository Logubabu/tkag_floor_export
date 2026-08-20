import os
import pytest
from app.etabs.e2k_parser import E2KParser
from app.models.intermediate import BuildingModel


def test_parse_sample_e2k():
    sample_path = os.path.join(os.path.dirname(__file__), "..", "..", "sample_models", "sample_building.e2k")
    assert os.path.exists(sample_path)

    with open(sample_path, "r") as f:
        content = f.read()

    parser = E2KParser()
    model: BuildingModel = parser.parse_string(content)

    assert len(model.stories) > 0
    assert any(st.name == "Level 5" for st in model.stories)
    assert len(model.nodes) > 0
    assert len(model.frames) > 0
    assert len(model.slabs) > 0
    assert len(model.materials) > 0
    assert len(model.shell_properties) > 0
