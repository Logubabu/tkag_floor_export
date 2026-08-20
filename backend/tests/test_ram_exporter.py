import os
import tempfile
import pytest
from app.models.intermediate import FloorModel, Story, Slab, Point2D
from app.ram_concept.exporter import RAMConceptExporter


def test_ram_concept_export_generation():
    story = Story(id="s5", name="Level 5", elevation=12.0, height=3.0)
    slab = Slab(
        id="SL1",
        story="Level 5",
        polygon=[Point2D(x=0, y=0), Point2D(x=10, y=0), Point2D(x=10, y=8), Point2D(x=0, y=8)],
        thickness=0.25
    )
    floor = FloorModel(story=story, slabs=[slab])
    exporter = RAMConceptExporter(floor)

    tmp_dir = tempfile.mkdtemp()
    res = exporter.generate_output(tmp_dir)

    assert res["success"] is True
    assert os.path.exists(res["dxf_file"])
    assert os.path.exists(res["automation_script"])
    assert os.path.exists(res["json_file"])
