import os
import sys
import logging
from typing import Tuple, Dict, Any, Optional

AGENT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPO_ROOT = os.path.abspath(os.path.join(AGENT_DIR, ".."))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")

for p in [AGENT_DIR, REPO_ROOT, BACKEND_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from app.models.intermediate import FloorModel

logger = logging.getLogger("RAMConceptAdapter")

class RAMConceptAdapter:
    """
    Adapter layer interfacing directly with official Bentley RAM Concept Python API on Windows.
    Generates CPT model files via RAM Concept API engine or DXF macro integration.
    """
    def __init__(self):
        self.api_available = False
        self._check_api()

    def _check_api(self):
        if sys.platform != "win32":
            self.api_available = False
            return
        try:
            import ramconcept # type: ignore
            self.api_available = hasattr(ramconcept, "Model")
        except ImportError:
            self.api_available = False

    def is_available(self) -> bool:
        return self.api_available

    def export_floor_to_cpt(self, floor_model: FloorModel, output_cpt_path: str) -> Tuple[bool, str]:
        """
        Creates/Populates a RAM Concept .CPT model using official RAM Concept API
        or python macro script bridge fallback.
        """
        try:
            if self.api_available:
                try:
                    import ramconcept # type: ignore
                    logger.info(f"Connecting to RAM Concept API engine for {floor_model.story.name}...")
                    model = ramconcept.Model.create(unit_set=ramconcept.UnitSet.SI)
                    
                    # Add Slabs
                    for slab in floor_model.slabs:
                        coords = [(pt.x, pt.y) for pt in slab.polygon]
                        thickness_m = slab.thickness
                        model.add_slab_area(polygon=coords, thickness=thickness_m)

                    # Add Openings
                    for op in floor_model.openings:
                        op_coords = [(pt.x, pt.y) for pt in op.polygon]
                        model.add_opening(polygon=op_coords)

                    model.save(output_cpt_path)
                    return True, f"RAM Concept model generated successfully at {output_cpt_path} via Python API."
                except Exception as api_err:
                    logger.warning(f"RAM Concept API execution failed ({api_err}), falling back to CPT exporter.")

            # Fallback to RAM Concept Macro Script / CPT file generation
            from app.ram_concept.exporter import RAMConceptExporter
            exporter = RAMConceptExporter(floor_model)
            res = exporter.generate_output_files()

            cpt_content = res.get("cpt_content") or exporter._generate_cpt()

            # Write CPT file payload
            mode = "wb" if isinstance(cpt_content, bytes) else "w"
            kwargs = {} if isinstance(cpt_content, bytes) else {"encoding": "utf-8"}
            with open(output_cpt_path, mode, **kwargs) as f:
                f.write(cpt_content)

            return True, f"RAM Concept package generated at {output_cpt_path} via fallback exporter."

        except Exception as e:
            logger.error(f"RAM Concept export failed: {e}")
            return False, f"RAM Concept export error: {e}"
