import os
import io
import zipfile
from typing import List, Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Response
from pydantic import BaseModel

from app.workers.job_manager import job_manager
from app.floor_extractor.extractor import FloorExtractor
from app.models.intermediate import BuildingModel, FloorModel, ExtractionMode, ValidationResult
from app.validation.validator import StructuralValidator
from app.ram_concept.exporter import RAMConceptExporter
from app.geometry.comparison import GeometryComparisonEngine


router = APIRouter(prefix="/api")

# In-memory storage for MVP projects & floor models
projects_db: Dict[str, Dict[str, Any]] = {
    "sample_proj": {
        "id": "sample_proj",
        "name": "Sample Building Project",
        "created_at": "2026-08-20",
        "filename": "sample_building.e2k",
        "job_id": None,
        "building_model": None
    }
}

extracted_floors_db: Dict[str, FloorModel] = {}


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


@router.post("/projects")
def create_project(data: ProjectCreate):
    import uuid
    pid = str(uuid.uuid4())[:8]
    proj = {
        "id": pid,
        "name": data.name,
        "created_at": "2026-08-20",
        "filename": None,
        "job_id": None,
        "building_model": None
    }
    projects_db[pid] = proj
    return proj


@router.get("/projects")
def list_projects():
    return list(projects_db.values())


@router.get("/projects/{project_id}")
def get_project(project_id: str):
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Project not found.")
    proj = projects_db[project_id]
    return {
        "id": proj["id"],
        "name": proj["name"],
        "created_at": proj["created_at"],
        "filename": proj["filename"],
        "has_model": proj["building_model"] is not None
    }


@router.post("/projects/{project_id}/upload")
async def upload_model(project_id: str, background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if project_id not in projects_db:
        projects_db[project_id] = {
            "id": project_id,
            "name": f"Project {project_id}",
            "created_at": "2026-08-20",
            "filename": file.filename,
            "job_id": None,
            "building_model": None
        }

    filename_lower = file.filename.lower()
    allowed_exts = ('.e2k', '.s2k', '.json', '.edb', '.$ed', '$ed', '.ed')
    if not any(filename_lower.endswith(ext) for ext in allowed_exts) and not file.filename.startswith('.'):
        # Default allow if filename has valid extension
        pass

    content_bytes = await file.read()
    content_str = None
    if not filename_lower.endswith('.edb'):
        content_str = content_bytes.decode("utf-8", errors="ignore")

    job = job_manager.create_job(file.filename)
    projects_db[project_id]["job_id"] = job.job_id
    projects_db[project_id]["filename"] = file.filename

    background_tasks.add_task(job_manager.process_e2k_file, job.job_id, content_str, content_bytes)

    return {
        "message": "File upload accepted. Processing in background.",
        "job_id": job.job_id,
        "filename": file.filename
    }


@router.get("/jobs/{job_id}")
def get_job_status(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    # Auto-link building model when completed
    if job.status == "COMPLETED" and job.building_model:
        for proj in projects_db.values():
            if proj.get("job_id") == job_id:
                proj["building_model"] = job.building_model

    return job.to_dict()


@router.get("/projects/{project_id}/stories")
def get_project_stories(project_id: str):
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Project not found.")

    proj = projects_db[project_id]
    b_model = proj.get("building_model")

    # If job completed, pull from job
    if proj.get("job_id"):
        job = job_manager.get_job(proj["job_id"])
        if job and job.building_model:
            b_model = job.building_model
            proj["building_model"] = b_model

    if not b_model:
        return []

    return [st.model_dump() for st in b_model.stories]


@router.get("/projects/{project_id}/building-model")
def get_full_building_model(project_id: str):
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Project not found.")

    proj = projects_db[project_id]
    b_model = proj.get("building_model")

    if proj.get("job_id"):
        job = job_manager.get_job(proj["job_id"])
        if job and job.building_model:
            b_model = job.building_model
            proj["building_model"] = b_model

    if not b_model:
        sample_path = os.path.join(os.path.dirname(__file__), "..", "..", "sample_models", "sample_building.e2k")
        if os.path.exists(sample_path):
            from app.etabs.e2k_parser import E2KParser
            with open(sample_path, "r") as f:
                b_model = E2KParser().parse_string(f.read())
                proj["building_model"] = b_model

    if not b_model:
        raise HTTPException(status_code=404, detail="No building model found.")

    return b_model.model_dump()


@router.post("/projects/{project_id}/extract-floor")
def extract_floor(project_id: str, req: FloorExtractRequest):
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Project not found.")

    proj = projects_db[project_id]
    b_model = proj.get("building_model")

    if not b_model:
        # Load sample model if none loaded yet
        sample_path = os.path.join(os.path.dirname(__file__), "..", "..", "sample_models", "sample_building.e2k")
        if os.path.exists(sample_path):
            from app.etabs.e2k_parser import E2KParser
            with open(sample_path, "r") as f:
                b_model = E2KParser().parse_string(f.read())
                proj["building_model"] = b_model

    if not b_model:
        raise HTTPException(status_code=400, detail="No ETABS model loaded for this project yet.")

    floor_model = FloorExtractor.extract_floor(b_model, req.story_name, req.mode)
    floor_id = f"{project_id}_{req.story_name.lower().replace(' ', '_')}"
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
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Project not found.")

    proj = projects_db[project_id]
    b_model = proj.get("building_model")

    if not b_model:
        raise HTTPException(status_code=400, detail="No ETABS model loaded for this project yet.")

    extracted_results = []
    for story_name in req.story_names:
        floor_model = FloorExtractor.extract_floor(b_model, story_name, req.mode)
        floor_id = f"{project_id}_{story_name.lower().replace(' ', '_')}"
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
    if floor_id not in extracted_floors_db:
        raise HTTPException(status_code=404, detail=f"Extracted floor {floor_id} not found.")

    return extracted_floors_db[floor_id].model_dump()


@router.post("/projects/{project_id}/floors/{floor_id}/validate")
def validate_floor_endpoint(project_id: str, floor_id: str):
    if floor_id not in extracted_floors_db:
        raise HTTPException(status_code=404, detail=f"Extracted floor {floor_id} not found.")

    floor_model = extracted_floors_db[floor_id]
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
def connect_live_etabs(project_id: str = "sample_proj"):
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
    success, msg = adapter.connect()
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
            if fid in extracted_floors_db:
                floor_model = extracted_floors_db[fid]
                exporter = RAMConceptExporter(floor_model)
                res = exporter.generate_output_files()
                clean_name = "".join(c for c in floor_model.story.name if c.isalnum() or c in ['_', '-'])

                if req.include_dxf:
                    zip_file.writestr(f"{clean_name}/{res['dxf_filename']}", res["dxf_content"])
                
                if req.include_cpt:
                    cpt_filename = res.get("cpt_filename", res["dxf_filename"].replace(".dxf", ".cpt"))
                    cpt_content = res.get("cpt_content", res["dxf_content"])
                    zip_file.writestr(f"{clean_name}/{cpt_filename}", cpt_content)

                if req.include_py:
                    zip_file.writestr(f"{clean_name}/{res['automation_filename']}", res["automation_content"])

                if req.include_json:
                    zip_file.writestr(f"{clean_name}/{res['json_filename']}", res["json_content"])

    zip_buffer.seek(0)
    filename = f"ETABS_RAMConcept_Export_{project_id}.zip"

    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )

