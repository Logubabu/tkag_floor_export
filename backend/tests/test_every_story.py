import os
import math
import pytest
from app.etabs.e2k_parser import E2KParser
from app.floor_extractor.extractor import FloorExtractor
from app.models.intermediate import ExtractionMode
from app.ram_concept.exporter import RAMConceptExporter

def test_every_story_in_all_sample_models():
    sample_dir = os.path.join(os.path.dirname(__file__), "..", "..", "sample_models")
    assert os.path.exists(sample_dir)

    sample_files = [f for f in os.listdir(sample_dir) if not f.startswith('.')]
    print(f"\nAudit {len(sample_files)} sample files in sample_models/: {sample_files}")

    for filename in sample_files:
        filepath = os.path.join(sample_dir, filename)
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        parser = E2KParser()
        building_model = parser.parse_string(content)
        print(f"\n==========================================")
        print(f"File: {filename} -> Total Stories: {len(building_model.stories)}")
        assert len(building_model.stories) > 0, f"No stories found in {filename}"

        for story in building_model.stories:
            floor_model = FloorExtractor.extract_floor(
                building_model, story.name, ExtractionMode.SLAB_AND_SUPPORTS
            )
            assert floor_model is not None, f"Floor extraction failed for story {story.name}"

            # Audit Slabs
            for slab in floor_model.slabs:
                assert slab.thickness > 0, f"Invalid slab thickness {slab.thickness} in story {story.name}"
                for pt in slab.polygon:
                    assert not math.isnan(pt.x) and not math.isnan(pt.y), f"NaN slab coord in story {story.name}"

            # Audit Openings
            for op in floor_model.openings:
                for pt in op.polygon:
                    assert not math.isnan(pt.x) and not math.isnan(pt.y), f"NaN opening coord in story {story.name}"

            # Audit Beams
            for bm in floor_model.beams:
                assert not math.isnan(bm.start_point.x) and not math.isnan(bm.start_point.y), f"NaN beam coord in story {story.name}"
                assert not math.isnan(bm.end_point.x) and not math.isnan(bm.end_point.y), f"NaN beam coord in story {story.name}"

            # Audit Columns Above & Below
            for col in floor_model.columns_above + floor_model.columns_below:
                assert not math.isnan(col.start_point.x) and not math.isnan(col.start_point.y), f"NaN column coord in story {story.name}"

            # Audit Walls Above & Below
            for wall in floor_model.walls_above + floor_model.walls_below:
                for pt in wall.polygon:
                    assert not math.isnan(pt.x) and not math.isnan(pt.y), f"NaN wall coord in story {story.name}"

            # Audit RAM Concept Exporter for story
            exporter = RAMConceptExporter(floor_model)
            out = exporter.generate_output_files()
            assert out["success"] is True
            assert len(out["cpt_content"]) > 0

            print(f"  Story [{story.name}] (Elev: {story.elevation}m): Slabs={len(floor_model.slabs)}, Beams={len(floor_model.beams)}, Cols={len(floor_model.columns_below)}, Walls={len(floor_model.walls_below)} -> CPT Export OK")
