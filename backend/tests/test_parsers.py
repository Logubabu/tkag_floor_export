import pytest
import os
from app.etabs.e2k_parser import E2KParser

def test_parse_e2k_sample():
    sample_path = os.path.join(os.path.dirname(__file__), "..", "..", "sample_models", "sample_building.e2k")
    assert os.path.exists(sample_path)
    with open(sample_path, "r") as f:
        content = f.read()
    parser = E2KParser()
    model = parser.parse_string(content)
    assert len(model.stories) > 0
    assert len(model.nodes) > 0

def test_parse_set_sample():
    set_path = os.path.join(os.path.dirname(__file__), "..", "..", "sample_models", "P-796-ULT-V22.3-UPDATED-01-06-2026.$et")
    assert os.path.exists(set_path)
    with open(set_path, "r", errors="ignore") as f:
        content = f.read()
    parser = E2KParser()
    model = parser.parse_string(content)
    assert len(model.stories) > 0
    assert len(model.slabs) > 0 or len(model.nodes) > 0

def test_parse_edb_binary_sample():
    edb_path = os.path.join(os.path.dirname(__file__), "..", "..", "sample_models", "P-796-ULT-V22.3-UPDATED-01-06-2026.EDB")
    assert os.path.exists(edb_path)
    with open(edb_path, "rb") as f:
        raw_bytes = f.read()
    parser = E2KParser()
    model = parser.parse_binary_edb_bytes(raw_bytes, "P-796-ULT.EDB")
    assert len(model.stories) > 0



def test_parse_edb_with_embedded_text_tables():
    raw_bytes = (
        b"ETABS           20.0\x00binary-prefix\x00"
        b'$ STORIES\nSTORY "Level 1" HEIGHT 3.5 ELEV 3.5\n'
        b'$ POINT COORDINATES\nPOINT "P1" 0 0 3.5\n'
    )
    model = E2KParser().parse_binary_edb_bytes(raw_bytes, "embedded.edb")
    assert model.project_name == "embedded.edb"
    assert [story.name for story in model.stories] == ["Level 1"]
    assert "P1" in model.nodes
