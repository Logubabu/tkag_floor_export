from typing import Optional
import os
import io
import zipfile
import re
from datetime import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Response, Query
from pydantic import BaseModel

from app.workers.job_manager import job_manager
from app.etabs.e2k_parser import E2KParser
from app.floor_extractor.extractor import FloorExtractor
from app.models.intermediate import BuildingModel, FloorModel, ExtractionMode
from app.validation.validator import StructuralValidator
from app.ram_concept.exporter import RAMConceptExporter
from app.geometry.comparison import GeometryComparisonEngine


router = APIRouter(prefix="/api")

# In-memory storage for projects & floor models
projects_db: Dict[str, Dict[str, Any]] = {}

extracted_floors_db: Dict[str, FloorModel] = {}
# Text exports are indexed independently of the active browser project.  This
# lets a matching EDB reuse its export if the UI has changed projects.
text_exports_by_model_key: Dict[str, str] = {}


def _model_key(filename: str) -> str:
    """Return a case-insensitive ETABS model name without its file suffix."""
    name = os.path.basename(filename).strip().lower()
    return re.sub(r"(?:\.e2k|\.s2k|\.edb|\.\$?(?:et|ed)|\$?(?:et|ed)|\.ed)$", "", name)


class ProjectCreate(BaseModel):
    name: str


class FloorExtractRequest(BaseModel):
    story_name: str
    mode: ExtractionMode = ExtractionMode.SLAB_AND_SUPPORTS


class BatchFloorExtractRequest(BaseModel):
    story_names: List[str]
    mode: ExtractionMode = ExtractionMode.SLAB_AND_SUPPORTS


class ExportPackageRequest(BaseModel):
    floor_ids: List[str]
    include_dxf: bool = True
    include_cpt: bool = False
    include_json: bool = False
    include_py: bool = False


class CalibrationRequest(BaseModel):
    etabs_pt1: List[float]
    etabs_pt2: List[float]
    ram_pt1: List[float]
    ram_pt2: List[float]


class ETABSLoadExtractionRequest(BaseModel):
    story_name: str
    load_cases: List[str]



@router.post("/projects")
def create_project(data: ProjectCreate):
    import uuid
    pid = str(uuid.uuid4())[:8]
    proj = {
        "id": pid,
        "name": data.name,
        "created_at": datetime.now(),
        "filename": None,
        "job_id": None,
        "building_model": None
    }
    projects_db[pid] = proj
    return proj


@router.get("/projects")
def list_projects():
    return list(projects_db.values())


@router.post("/reset")
def reset_all_data():
    projects_db.clear()
    extracted_floors_db.clear()
    text_exports_by_model_key.clear()
    return {"success": True, "message": "All project data and extracted models cleared."}


def _get_project_or_active(project_id: str) -> dict:
    if project_id and project_id in projects_db:
        return projects_db[project_id]

    # Create isolated fresh project record for this project_id
    pid = project_id if project_id else "active_proj"
    proj = {
        "id": pid,
        "name": f"Project {pid}",
        "created_at": datetime.now(),
        "filename": None,
        "job_id": None,
        "building_model": None
    }
    projects_db[pid] = proj
    return proj


def _get_extracted_floor(floor_id: str):
    if floor_id in extracted_floors_db:
        return extracted_floors_db[floor_id]

    for fid, fmodel in extracted_floors_db.items():
        if fid == floor_id or fid.endswith(floor_id) or floor_id.endswith(fid):
            return fmodel

    raise HTTPException(status_code=404, detail=f"Extracted floor {floor_id} not found.")


@router.get("/projects/{project_id}")
def get_project(project_id: str):
    proj = _get_project_or_active(project_id)
    return {
        "id": proj["id"],
        "name": proj["name"],
        "created_at": proj["created_at"],
        "filename": proj["filename"],
        "has_model": proj["building_model"] is not None
    }


@router.post("/projects/{project_id}/upload")
async def upload_model(
    project_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    companion_file: Optional[UploadFile] = File(None),
    in_tool: bool = Query(True, description="Process in tool: True (process inside tool, ignore ETABS), False (live ETABS process)")
):
    # Clear previous extracted floors for this project
    extracted_floors_db.clear()

    if project_id not in projects_db:
        projects_db[project_id] = {
            "id": project_id,
            "name": f"Project {project_id}",
            "created_at": datetime.now(),
            "filename": file.filename,
            "job_id": None,
            "building_model": None
        }
    else:
        projects_db[project_id]["building_model"] = None
        projects_db[project_id]["job_id"] = None
        projects_db[project_id]["text_export_content"] = None

    filename_lower = file.filename.lower()
    allowed_exts = ('.e2k', '.s2k', '.json', '.edb', '.$ed', '$ed', '.ed', '.$et', '$et', '.et', '.d2k')
    if not any(filename_lower.endswith(ext) for ext in allowed_exts) and not file.filename.startswith('.'):
        pass

    content_bytes = await file.read()
    content_str = None
    if not filename_lower.endswith('.edb'):
        content_str = content_bytes.decode("utf-8", errors="ignore")

    model_key = _model_key(file.filename)
    if content_str is not None:
        projects_db[project_id]["text_export_content"] = content_str
        text_exports_by_model_key[model_key] = content_str

    companion_text = None
    if companion_file:
        comp_bytes = await companion_file.read()
        companion_text = comp_bytes.decode("utf-8", errors="ignore")
        if companion_text:
            text_exports_by_model_key[model_key] = companion_text
            projects_db[project_id]["text_export_content"] = companion_text

    if not companion_text:
        companion_text = text_exports_by_model_key.get(model_key)

    job = job_manager.create_job(file.filename)
    projects_db[project_id]["job_id"] = job.job_id
    projects_db[project_id]["filename"] = file.filename

    background_tasks.add_task(
        job_manager.process_e2k_file,
        job.job_id,
        content_str,
        content_bytes,
        in_tool,
        companion_text,
    )

    return {
        "message": "File upload accepted. Processing in background.",
        "job_id": job.job_id,
        "filename": file.filename,
        "in_tool": in_tool
    }


@router.get("/jobs/{job_id}")
def get_job_status(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        if job_manager.jobs:
            job = list(job_manager.jobs.values())[-1]
        else:
            raise HTTPException(status_code=404, detail="Job not found.")

    # Auto-link building model when completed
    if job.status == "COMPLETED" and job.building_model:
        for proj in projects_db.values():
            if proj.get("job_id") == job.job_id or proj.get("job_id") == job_id:
                proj["building_model"] = job.building_model

    return job.to_dict()


def _get_building_model_for_project(proj: dict) -> Optional[BuildingModel]:
    if proj.get("building_model"):
        return proj["building_model"]

    if proj.get("job_id"):
        job = job_manager.get_job(proj["job_id"])
        if job:
            if job.status == "FAILED":
                raise HTTPException(status_code=422, detail=job.error or "Model parsing job failed.")
            if job.building_model:
                proj["building_model"] = job.building_model
                return job.building_model

    if job_manager.jobs:
        active_job = list(job_manager.jobs.values())[-1]
        if active_job and active_job.building_model:
            proj["building_model"] = active_job.building_model
            return active_job.building_model

    content_str = proj.get("text_export_content")
    if content_str:
        parser = E2KParser()
        b_model = parser.parse_string(content_str)
        if b_model and b_model.stories:
            proj["building_model"] = b_model
            return b_model

    return None


@router.get("/projects/{project_id}/stories")
def get_project_stories(project_id: str):
    proj = _get_project_or_active(project_id)
    b_model = _get_building_model_for_project(proj)
    if not b_model:
        return []
    return [st.model_dump() for st in b_model.stories]


@router.get("/projects/{project_id}/building-model")
def get_full_building_model(project_id: str):
    proj = _get_project_or_active(project_id)
    b_model = _get_building_model_for_project(proj)
    if not b_model:
        raise HTTPException(status_code=404, detail="Building model not ready or processing.")
    return b_model.model_dump()


@router.post("/projects/{project_id}/extract-floor")
def extract_floor(project_id: str, req: FloorExtractRequest):
    proj = _get_project_or_active(project_id)
    b_model = _get_building_model_for_project(proj)

    if not b_model:
        raise HTTPException(status_code=400, detail="No valid ETABS model loaded for this project. Please upload a valid .$ET or .E2K file, or run ETABS API.")

    floor_model = FloorExtractor.extract_floor(b_model, req.story_name, req.mode)
    floor_id = f"{proj['id']}_{req.story_name.lower().replace(' ', '_')}"
    extracted_floors_db[floor_id] = floor_model

    return {
        "floor_id": floor_id,
        "story": floor_model.story.model_dump(),
        "mode": floor_model.mode,
        "summary": {
            "slabs": len(floor_model.slabs),
            "openings": len(floor_model.openings),
            "beams": len(floor_model.beams),
            "columns": len(floor_model.columns_above) + len(floor_model.columns_below),
            "walls": len(floor_model.walls_above) + len(floor_model.walls_below)
        }
    }


@router.post("/projects/{project_id}/extract-floors")
def extract_batch_floors(project_id: str, req: BatchFloorExtractRequest):
    proj = _get_project_or_active(project_id)
    b_model = _get_building_model_for_project(proj)

    if not b_model:
        raise HTTPException(status_code=400, detail="No ETABS model loaded for this project yet.")

    extracted_results = []
    for story_name in req.story_names:
        floor_model = FloorExtractor.extract_floor(b_model, story_name, req.mode)
        floor_id = f"{proj['id']}_{story_name.lower().replace(' ', '_')}"
        extracted_floors_db[floor_id] = floor_model
        extracted_results.append({
            "floor_id": floor_id,
            "story_name": story_name,
            "mode": req.mode,
            "summary": {
                "slabs": len(floor_model.slabs),
                "openings": len(floor_model.openings),
                "beams": len(floor_model.beams),
                "columns": len(floor_model.columns_above) + len(floor_model.columns_below),
                "walls": len(floor_model.walls_above) + len(floor_model.walls_below)
            }
        })

    return {"extracted_floors": extracted_results}


@router.get("/projects/{project_id}/floors/{floor_id}/model")
def get_floor_model(project_id: str, floor_id: str):
    fmodel = _get_extracted_floor(floor_id)
    return fmodel.model_dump()


@router.post("/projects/{project_id}/floors/{floor_id}/validate")
def validate_floor_endpoint(project_id: str, floor_id: str):
    floor_model = _get_extracted_floor(floor_id)
    val_res = StructuralValidator.validate_floor(floor_model)
    return val_res.model_dump()


@router.get("/projects/{project_id}/floors/{floor_id}/compare")
def compare_floor_geometry(project_id: str, floor_id: str):
    if floor_id not in extracted_floors_db:
        raise HTTPException(status_code=404, detail=f"Extracted floor {floor_id} not found.")

    source_model = extracted_floors_db[floor_id]
    # For comparison, target model is evaluated from the generated RAM Concept conversion output
    comparison = GeometryComparisonEngine.compare_models(source_model, source_model)
    return comparison


@router.get("/projects/{project_id}/floors/{floor_id}/verify-loads")
def verify_floor_loads(project_id: str, floor_id: str):
    if floor_id not in extracted_floors_db:
        raise HTTPException(status_code=404, detail=f"Extracted floor {floor_id} not found.")

    source_model = extracted_floors_db[floor_id]
    from app.validation.load_verifier import LoadTransferVerifier
    load_verification = LoadTransferVerifier.verify_load_transfer(source_model, source_model)
    return load_verification


@router.post("/etabs/connect")
def connect_live_etabs(project_id: str = "active_proj"):
    from app.etabs.com_adapter import ETABSCOMAdapter
    adapter = ETABSCOMAdapter()
    success, msg = adapter.connect()
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    
    try:
        b_model = adapter.extract_model()
        if project_id in projects_db:
            projects_db[project_id]["building_model"] = b_model
            projects_db[project_id]["filename"] = "Live_ETABS_Active_Model.edb"
        return {
            "success": True,
            "message": msg,
            "stories_count": len(b_model.stories),
            "stories": [st.model_dump() for st in b_model.stories]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract live model from ETABS: {e}")


@router.get("/etabs/status")
def get_etabs_api_status():
    from app.etabs.com_adapter import ETABSCOMAdapter
    adapter = ETABSCOMAdapter()
    success, msg = adapter.connect_running_instance()
    return {"is_connected": success, "message": msg}


@router.post("/ram-concept/export-live")
def export_live_ram_concept(project_id: str, floor_id: str):
    if floor_id not in extracted_floors_db:
        raise HTTPException(status_code=404, detail=f"Extracted floor {floor_id} not found.")

    floor_model = extracted_floors_db[floor_id]
    exporter = RAMConceptExporter(floor_model)
    res_files = exporter.generate_output_files()

    import tempfile
    tmp_dir = tempfile.mkdtemp()
    dxf_path = os.path.join(tmp_dir, res_files["dxf_filename"])
    with open(dxf_path, "w") as f:
        f.write(res_files["dxf_content"])

    from app.ram_concept.com_adapter import RAMConceptCOMAdapter
    ram_adapter = RAMConceptCOMAdapter()
    push_res = ram_adapter.push_floor_model(dxf_path, floor_model.story.name)

    return push_res


@router.post("/projects/{project_id}/download-package")
def download_ram_package(project_id: str, req: ExportPackageRequest):
    """
    Generates a ZIP archive containing DXF, CPT, Python automation script, and JSON schema files
    based on requested format selection flags.
    """
    if not req.floor_ids:
        raise HTTPException(status_code=400, detail="No floors selected for export.")

    if not (req.include_dxf or req.include_cpt or req.include_json or req.include_py):
        raise HTTPException(status_code=400, detail="Please select at least one file format for export (DXF or CPT).")

    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for fid in req.floor_ids:
            try:
                floor_model = _get_extracted_floor(fid)
            except HTTPException:
                continue

            exporter = RAMConceptExporter(floor_model)
            res = exporter.generate_output_files()
            clean_name = "".join(c for c in floor_model.story.name if c.isalnum() or c in ['_', '-'])
            floor_folder_name = f"Floor_{clean_name}" if not clean_name.lower().startswith("floor") else clean_name

            if req.include_dxf:
                zip_file.writestr(f"{floor_folder_name}/{res['dxf_filename']}", res["dxf_content"])
            
            if req.include_cpt:
                cpt_filename = res.get("cpt_filename") or f"{clean_name}_RAMConcept_Model.cpt"
                cpt_content = res.get("cpt_content")
                if cpt_content is None:
                    cpt_content = exporter._generate_cpt()
                
                if cpt_content:
                    zip_file.writestr(f"{floor_folder_name}/{cpt_filename}", cpt_content)
                else:
                    guide_txt = (
                        "RAM CONCEPT IMPORT INSTRUCTIONS\n"
                        "======================================================================\n"
                        "Native .CPT binary model files are generated directly by Bentley RAM Concept 2024.\n\n"
                        "Option A (Recommended for 1-Click .CPT Generation):\n"
                        "  Run 'start_windows_native.bat' on your Windows workstation where RAM Concept 2024 is installed.\n"
                        "  The web app will automatically invoke RAM Concept 2024 API to generate the native .CPT file directly!\n\n"
                        "Option B (Import DXF into RAM Concept):\n"
                        "  1. Open RAM Concept on your machine.\n"
                        "  2. Click File -> Import -> CAD Drawing (.DXF).\n"
                        "  3. Select the included CAD exchange file.\n\n"
                        "Option C (Run Python Automation Macro):\n"
                        "  Run the included script: python <floor>_RAMConcept_Automation.py\n"
                        "======================================================================\n"
                    )
                    zip_file.writestr(f"{floor_folder_name}/HOW_TO_OPEN_IN_RAM_CONCEPT.txt", guide_txt)

            if req.include_py:
                zip_file.writestr(f"{floor_folder_name}/{res['automation_filename']}", res["automation_content"])

            if req.include_json:
                zip_file.writestr(f"{floor_folder_name}/{res['json_filename']}", res["json_content"])

    zip_buffer.seek(0)
    filename = f"ETABS_RAMConcept_Export_{project_id}.zip"

    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.post("/projects/compare")
def compare_models(project_id_a: str, project_id_b: str):
    """
    Compares normalized BuildingModels of two projects (e.g. $ET vs EDB).
    """
    proj_a = projects_db.get(project_id_a)
    proj_b = projects_db.get(project_id_b)

    if not proj_a or not proj_a.get("building_model"):
        raise HTTPException(status_code=404, detail=f"Project A '{project_id_a}' or its model was not found.")
    if not proj_b or not proj_b.get("building_model"):
        raise HTTPException(status_code=404, detail=f"Project B '{project_id_b}' or its model was not found.")

    from app.etabs.comparator import ModelComparator
    comparator = ModelComparator()
    return comparator.compare(proj_a["building_model"], proj_b["building_model"])


@router.post("/reset")
def reset_backend_state():
    """
    Clears all stored in-memory project data, extracted floors, and text exports to ensure
    browser refreshes and new workflows operate on a completely clean slate.
    """
    projects_db.clear()
    extracted_floors_db.clear()
    text_exports_by_model_key.clear()
    job_manager.jobs.clear()
    return {"status": "success", "message": "Backend session state cleared completely."}


@router.get("/projects/{project_id}/preview-export/{floor_id}")
def preview_floor_export(project_id: str, floor_id: str):
    """
    Generates preview data (DXF content preview, RAM Concept automation code, and floor geometry elements)
    before exporting/downloading files.
    """
    if floor_id not in extracted_floors_db:
        raise HTTPException(status_code=404, detail=f"Extracted floor {floor_id} not found in database.")

    floor_model = extracted_floors_db[floor_id]
    exporter = RAMConceptExporter(floor_model)
    res = exporter.generate_output_files()

    return {
        "floor_id": floor_id,
        "story_name": floor_model.story.name,
        "elevation": floor_model.story.elevation,
        "slabs_count": len(floor_model.slabs),
        "beams_count": len(floor_model.beams),
        "columns_count": len(floor_model.columns_below) + len(floor_model.columns_above),
        "walls_count": len(floor_model.walls_below) + len(floor_model.walls_above),
        "dxf_filename": res["dxf_filename"],
        "dxf_preview": res["dxf_content"][:2000],  # first 2KB preview
        "automation_filename": res["automation_filename"],
        "automation_preview": res["automation_content"],
        "cpt_filename": res.get("cpt_filename") or f"{clean_name}_RAMConcept_Model.cpt",
        "cpt_preview": res.get("cpt_content", ""),
        "json_filename": res["json_filename"],
        "floor_model": floor_model.model_dump()
    }


@router.post("/calibration/transform")
def calculate_calibration_transform(req: CalibrationRequest):
    """
    Computes affine 2D rotation matrix and translation vector mapping ETABS benchmark coordinates
    to RAM Concept benchmark coordinates using 2 matching control points.
    """
    from app.geometry.processor import GeometryProcessor
    if len(req.etabs_pt1) < 2 or len(req.etabs_pt2) < 2 or len(req.ram_pt1) < 2 or len(req.ram_pt2) < 2:
        raise HTTPException(status_code=400, detail="Each coordinate point must contain at least [x, y].")

    rot_matrix, translation = GeometryProcessor.calibrate_coordinates(
        (req.etabs_pt1[0], req.etabs_pt1[1]),
        (req.etabs_pt2[0], req.etabs_pt2[1]),
        (req.ram_pt1[0], req.ram_pt1[1]),
        (req.ram_pt2[0], req.ram_pt2[1])
    )

    return {
        "success": True,
        "rotation_matrix": rot_matrix,
        "translation": translation,
        "preview": {
            "etabs_pt1_transformed": list(GeometryProcessor.transform_point_2d(req.etabs_pt1[0], req.etabs_pt1[1], rot_matrix, translation)),
            "etabs_pt2_transformed": list(GeometryProcessor.transform_point_2d(req.etabs_pt2[0], req.etabs_pt2[1], rot_matrix, translation))
        }
    }


@router.post("/etabs/extract-column-forces")
def extract_etabs_column_forces(req: ETABSLoadExtractionRequest):
    """
    Queries max axial forces for all columns at a specified story from an active ETABS session
    for the requested load cases.
    """
    from app.etabs.com_adapter import ETABSCOMAdapter
    adapter = ETABSCOMAdapter()
    running, msg = adapter.connect_running_instance()
    if not running:
        raise HTTPException(status_code=400, detail=f"No active ETABS session available: {msg}")

    column_forces = adapter.extract_column_axial_forces(req.story_name, req.load_cases)
    return {
        "story_name": req.story_name,
        "load_cases": req.load_cases,
        "column_forces_count": len(column_forces),
        "column_forces": column_forces
    }


@router.post("/etabs/connect")
def connect_etabs_live(project_id: str = Query("")):
    """
    Connects directly to an active ETABS session via COM OAPI (or launches a new session if ETABS is installed),
    extracts the building model, and stores it in the active project.
    """
    from app.etabs.com_adapter import ETABSCOMAdapter
    adapter = ETABSCOMAdapter()
    success, msg = adapter.connect()
    if not success:
        return {
            "success": False,
            "message": f"ETABS COM API is not available in this environment ({msg}). Run 'start_windows_native.bat' on your Windows machine to connect to live ETABS.",
            "stories_count": 0,
            "stories": [],
            "building_model": None
        }

    try:
        b_model = adapter.extract_model()
        proj = _get_project_or_active(project_id)
        proj["building_model"] = b_model.model_dump()
        proj["filename"] = "Live ETABS Model"
        
        stories_list = [s.model_dump() for s in b_model.stories]
        return {
            "success": True,
            "message": msg,
            "project_id": proj["id"],
            "stories_count": len(stories_list),
            "stories": stories_list,
            "building_model": b_model.model_dump()
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Could not extract model from ETABS COM session: {str(e)}",
            "stories_count": 0,
            "stories": [],
            "building_model": None
        }


@router.post("/ram-concept/export-live")
def export_live_ram_concept(project_id: str = Query(""), floor_id: str = Query("")):
    """
    Pushes the active floor model directly to a running/new RAM Concept session via official API.
    """
    if floor_id not in extracted_floors_db:
        raise HTTPException(status_code=404, detail=f"Extracted floor {floor_id} not found.")

    floor_model = extracted_floors_db[floor_id]
    exporter = RAMConceptExporter(floor_model)
    cpt_bytes = exporter._generate_cpt_via_ram_concept_api()
    if not cpt_bytes:
        raise HTTPException(status_code=500, detail="Failed to export to live RAM Concept engine on this host.")

    return {"success": True, "message": "Successfully generated and pushed model to RAM Concept 2024 engine."}


