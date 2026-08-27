import os
import sys
import logging
import time
from typing import Dict, Any, Optional

AGENT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPO_ROOT = os.path.abspath(os.path.join(AGENT_DIR, ".."))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")

for p in [AGENT_DIR, REPO_ROOT, BACKEND_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from etabs.client import ETABSAdapter
    from ramconcept.client import RAMConceptAdapter
except ModuleNotFoundError:
    from conversionagent.etabs.client import ETABSAdapter
    from conversionagent.ramconcept.client import RAMConceptAdapter

from app.geometry.comparison import GeometryComparisonEngine
from app.models.intermediate import FloorModel, ExtractionMode

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
logger = logging.getLogger("ConversionPipeline")

class ConversionPipeline:
    """
    Orchestrates the entire conversion workflow:
    ETABS Ingestion -> Floor Geometry Extraction -> Normalization -> RAM Concept Generation -> Comparison
    """
    def __init__(self):
        self.etabs_adapter = ETABSAdapter()
        self.ram_adapter = RAMConceptAdapter()

    def run_conversion(
        self,
        edb_file_path: str,
        story_name: str,
        output_cpt_path: str,
        mode: ExtractionMode = ExtractionMode.SLAB_AND_SUPPORTS
    ) -> Dict[str, Any]:
        logs = []
        logs.append(f"[INFO] Initializing conversion pipeline for model: {os.path.basename(edb_file_path)}")
        logs.append(f"[INFO] Target story: {story_name}")

        start_time = time.time()

        # Step 1: Connect / Open ETABS
        ok, msg = self.etabs_adapter.connect()
        logs.append(f"[{'INFO' if ok else 'WARNING'}] ETABS Connection: {msg}")

        # Step 2: Extract Floor Model (Using backend E2K fallback if OAPI unavailable)
        building_model = None
        if ok:
            open_ok, open_msg = self.etabs_adapter.open_model(edb_file_path)
            logs.append(f"[{'INFO' if open_ok else 'ERROR'}] Opening file: {open_msg}")
        
        # Load from E2K parser if file is text or fallback
        if not building_model and (edb_file_path.lower().endswith(('.e2k', '.$et', '.s2k')) or not ok):
            from app.etabs.e2k_parser import E2KParser
            logs.append("[INFO] Parsing model geometry using E2K Text Parser...")
            with open(edb_file_path, "r", encoding="utf-8", errors="ignore") as f:
                building_model = E2KParser().parse_string(f.read())
            logs.append(f"[INFO] Parsed building model with {len(building_model.stories)} stories.")

        if not building_model:
            return {
                "success": False,
                "error": "Failed to parse ETABS model geometry.",
                "logs": logs
            }

        # Step 3: Extract Selected Floor Model
        from app.floor_extractor.extractor import FloorExtractor
        logs.append(f"[INFO] Extracting floor geometry for story '{story_name}'...")
        floor_model = FloorExtractor.extract_floor(building_model, story_name, mode)
        logs.append(f"[INFO] Extracted {len(floor_model.slabs)} slabs, {len(floor_model.openings)} openings, {len(floor_model.beams)} beams.")

        # Step 4: Validate Geometry
        from app.validation.validator import StructuralValidator
        val_res = StructuralValidator.validate_floor(floor_model)
        logs.append(f"[INFO] Structural Validation Result: Valid={val_res.is_valid}, Alerts={len(val_res.alerts)}")

        # Step 5: Export RAM Concept Model
        logs.append(f"[INFO] Generating RAM Concept model at: {output_cpt_path}")
        ram_ok, ram_msg = self.ram_adapter.export_floor_to_cpt(floor_model, output_cpt_path)
        logs.append(f"[{'INFO' if ram_ok else 'ERROR'}] RAM Concept Export: {ram_msg}")

        # Step 6: Visual & Geometry Comparison
        comparison = GeometryComparisonEngine.compare_models(floor_model, floor_model)

        elapsed = round(time.time() - start_time, 2)
        logs.append(f"[INFO] Conversion pipeline completed in {elapsed}s.")

        return {
            "success": ram_ok,
            "elapsed_seconds": elapsed,
            "story_name": story_name,
            "output_file": output_cpt_path,
            "summary": {
                "slabs": len(floor_model.slabs),
                "openings": len(floor_model.openings),
                "beams": len(floor_model.beams),
                "columns": len(floor_model.columns_above) + len(floor_model.columns_below),
                "walls": len(floor_model.walls_above) + len(floor_model.walls_below)
            },
            "comparison": comparison,
            "logs": logs
        }
