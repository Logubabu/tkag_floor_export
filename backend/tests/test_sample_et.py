import os
import pytest
from app.etabs.e2k_parser import E2KParser

def test_parse_sample_et_file():
    filepath = os.path.join(os.path.dirname(__file__), "..", "..", "sample_models", "P-796-ULT-V22.3-UPDATED-01-06-2026.$et")
    assert os.path.exists(filepath)
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    parser = E2KParser()
    model = parser.parse_string(content)

    print(f"Extracted {len(model.stories)} stories from $et file:")
    for st in model.stories:
        print(f" - Story: {st.name}, Elevation: {st.elevation}")

    assert len(model.stories) > 0
