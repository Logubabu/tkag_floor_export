import os
import pytest
from app.etabs.e2k_parser import E2KParser
from app.floor_extractor.extractor import FloorExtractor
from app.models.intermediate import ExtractionMode
from app.ram_concept.exporter import RAMConceptExporter

def test_all_sample_models_exist_and_parse():
    sample_dir = os.path.join(os.path.dirname(__file__), "..", "..", "sample_models")
    assert os.path.exists(sample_dir)

    sample_files = [f for f in os.listdir(sample_dir) if not f.startswith('.')]
    print(f"\nFound {len(sample_files)} sample model files in sample_models/:", sample_files)

    for filename in sample_files:
        filepath = os.path.join(sample_dir, filename)
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        parser = E2KParser()
        building_model = parser.parse_string(content)
        print(f"\n[File: {filename}] Extracted {len(building_model.stories)} stories.")
        assert len(building_model.stories) > 0

        # Extract floor model for first story
        first_story = building_model.stories[0]
        floor_model = FloorExtractor.extract_floor(building_model, first_story.name, ExtractionMode.SLAB_AND_SUPPORTS)
        assert floor_model is not None
        assert floor_model.story.name == first_story.name

        # Export RAM Concept package (.cpt, .dxf, .py, .json)
        exporter = RAMConceptExporter(floor_model)
        export_files = exporter.generate_output_files()

        assert export_files["success"] is True
        assert "cpt_filename" in export_files and export_files["cpt_filename"].endswith(".cpt")
        assert "dxf_filename" in export_files and export_files["dxf_filename"].endswith(".dxf")
        assert "automation_filename" in export_files and export_files["automation_filename"].endswith(".py")
        assert "json_filename" in export_files and export_files["json_filename"].endswith(".json")

        assert len(export_files["cpt_content"]) > 0
        assert len(export_files["dxf_content"]) > 0
        print(f"  -> Generated RAM Concept .cpt file: {export_files['cpt_filename']} ({len(export_files['cpt_content'])} bytes)")
        print(f"  -> Generated CAD .dxf file: {export_files['dxf_filename']} ({len(export_files['dxf_content'])} bytes)")
