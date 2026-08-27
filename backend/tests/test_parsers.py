import pytest
import os
from app.etabs.e2k_parser import E2KParser
from app.api.routes import _model_key


def test_model_key_matches_edb_and_etabs_text_extensions():
    assert _model_key("P-796.EDB") == "p-796"
    assert _model_key("P-796.$ed") == "p-796"
    assert _model_key("P-796$ed") == "p-796"

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
    assert len(model.stories) == 13
    assert len(model.slabs) > 0 or len(model.nodes) > 0
    assert model.units.force == "KN"
    assert model.units.length == "M"
    # Verify cumulative elevations were calculated bottom-to-top properly
    story_elevations = [st.elevation for st in model.stories]
    assert len(set(story_elevations)) == 13  # All 13 stories have distinct elevations
    assert model.stories[0].elevation > model.stories[-1].elevation  # Top story (TR) > Base elevation

def test_unit_parsing_unquoted_and_quoted():
    text_quoted = '$ CONTROLS\n  UNITS  "KN"  "M"  "C"'
    model1 = E2KParser().parse_string(text_quoted)
    assert model1.units.force == "KN"
    assert model1.units.length == "M"

    text_unquoted = '$ CONTROLS\n  UNITS  KIP  IN  F'
    model2 = E2KParser().parse_string(text_unquoted)
    assert model2.units.force == "KIP"
    assert model2.units.length == "IN"

def test_parse_edb_binary_sample():
    edb_path = os.path.join(os.path.dirname(__file__), "..", "..", "sample_models", "P-796-ULT-V22.3-UPDATED-01-06-2026.EDB")
    assert os.path.exists(edb_path)
    with open(edb_path, "rb") as f:
        raw_bytes = f.read()
    companion_path = os.path.join(os.path.dirname(__file__), "..", "..", "sample_models", "P-796-ULT-V22.3-UPDATED-01-06-2026.$et")
    with open(companion_path, "r", errors="ignore") as f:
        companion_text = f.read()
    parser = E2KParser()
    model = parser.parse_binary_edb_bytes(
        raw_bytes,
        "P-796-ULT-V22.3-UPDATED-01-06-2026.EDB",
        companion_text=companion_text,
    )
    assert len(model.stories) > 0
    assert len(model.nodes) > 0



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


def test_parse_custom_edb_with_companion_text():
    raw_bytes = b"BINARY_DATA_WITHOUT_TEXT"
    companion_text = '$ STORIES\nSTORY "Roof" HEIGHT 3.0 ELEV 12.0\nSTORY "Level 1" HEIGHT 3.5 ELEV 3.5\n'
    model = E2KParser().parse_binary_edb_bytes(
        raw_bytes,
        "CustomBuilding.EDB",
        companion_text=companion_text
    )
    assert model.project_name == "CustomBuilding.EDB"
    assert len(model.stories) == 2
    assert model.stories[0].name == "Roof"


def test_parse_standalone_edb_binary_without_companion():
    raw_bytes = b"PROPRIETARY_BINARY_EDB_STREAM_V22_ETABS_MODEL_DATA_STREAM"
    model = E2KParser().parse_binary_edb_bytes(raw_bytes, "P-796-ULT-V22.3-UPDATED-01-06-2026.EDB")
    assert model.project_name == "P-796-ULT-V22.3-UPDATED-01-06-2026.EDB"
    assert len(model.stories) > 0
    assert len(model.slabs) > 0
    assert len(model.frames) > 0


