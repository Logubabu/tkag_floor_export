import os
from typing import Dict, Any, List
from app.models.intermediate import BuildingModel
from app.floor_extractor.extractor import FloorExtractor
from app.conversion.converter import StructuralConverter
from app.validation.validator import StructuralValidator
from app.ram_concept.exporter import RAMConceptExporter
from app.reports.report_generator import ReportGenerator


class ExportService:
    """
    High-level Orchestration Service for ETABS to RAM Concept export pipeline.
    Handles extraction, conversion, validation, RAM Concept CPT export, verification, and report generation.
    """
    def __init__(self, building_model: BuildingModel):
        self.building_model = building_model

    def export_stories(self, selected_stories: List[str], output_dir: str) -> Dict[str, Any]:
        results = []
        os.makedirs(output_dir, exist_ok=True)

        for story_name in selected_stories:
            floor = FloorExtractor.extract_floor(self.building_model, story_name)
            validation_res = StructuralValidator.validate_floor(floor)
            converter = StructuralConverter(floor)
            conversion = converter.convert_floor()

            exporter = RAMConceptExporter(floor)
            export_res = exporter.generate_output(output_dir)

            report_path = ReportGenerator.generate_report(
                story_name=story_name,
                conversion_summary=conversion["summary"],
                validation_data=validation_res.model_dump(),
                export_result=export_res,
                output_dir=output_dir
            )

            results.append({
                "story": story_name,
                "success": export_res.get("success", False),
                "cpt_file": export_res.get("cpt_file", ""),
                "dxf_file": export_res.get("dxf_file", ""),
                "report_file": report_path,
                "validation": validation_res.model_dump()
            })

        return {
            "success": True,
            "total_stories": len(selected_stories),
            "successful_stories": len([r for r in results if r["success"]]),
            "results": results
        }
