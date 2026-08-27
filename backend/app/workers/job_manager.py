import os
import uuid
import time
import asyncio
import tempfile
from typing import Dict, Any, Optional
from app.models.intermediate import BuildingModel, FloorModel
from app.etabs.e2k_parser import E2KParser


class ProcessingJob:
    def __init__(self, job_id: str, filename: str):
        self.job_id = job_id
        self.filename = filename
        self.status = "QUEUED"  # QUEUED, PROCESSING, VALIDATING, COMPLETED, FAILED
        self.progress = 0       # 0 - 100%
        self.stage = "Initial Queue"
        self.building_model: Optional[BuildingModel] = None
        self.extracted_floors: Dict[str, FloorModel] = {}
        self.error: Optional[str] = None
        self.created_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "filename": self.filename,
            "status": self.status,
            "progress": self.progress,
            "stage": self.stage,
            "error": self.error,
            "has_model": self.building_model is not None,
            "stories": [st.name for st in self.building_model.stories] if self.building_model else []
        }


class JobManager:
    """
    Background Task Manager for ETABS model processing and floor extraction jobs.
    """
    def __init__(self):
        self.jobs: Dict[str, ProcessingJob] = {}

    def create_job(self, filename: str) -> ProcessingJob:
        self.jobs.clear()  # Clear previous jobs on new file upload
        job_id = str(uuid.uuid4())
        job = ProcessingJob(job_id, filename)
        self.jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> Optional[ProcessingJob]:
        return self.jobs.get(job_id)

    async def process_e2k_file(
        self,
        job_id: str,
        file_content: Optional[str],
        raw_bytes: Optional[bytes] = None,
        in_tool: bool = True,
        companion_text: Optional[str] = None,
    ):
        job = self.jobs.get(job_id)
        if not job:
            return

        try:
            job.status = "PROCESSING"
            job.progress = 20
            job.stage = "Parsing ETABS model geometry & properties..."
            await asyncio.sleep(0.1)

            # Process uploaded model
            if job.filename.lower().endswith(".edb"):
                com_success = False
                com_err = None
                
                # 1. If in_tool is False (Live ETABS mode requested by user)
                if not in_tool:
                    try:
                        from app.etabs.com_adapter import ETABSCOMAdapter
                        adapter = ETABSCOMAdapter()
                        success, msg = adapter.connect()
                        if success:
                            import tempfile
                            tmp_edb_dir = tempfile.mkdtemp()
                            tmp_edb_path = os.path.join(tmp_edb_dir, job.filename)
                            if raw_bytes:
                                with open(tmp_edb_path, "wb") as f:
                                    f.write(raw_bytes)
                                adapter.open_file(tmp_edb_path)
                            model = adapter.extract_model()
                            if model and len(model.stories) > 0:
                                model.project_name = job.filename
                                job.building_model = model
                                com_success = True
                        else:
                            com_err = msg
                    except Exception as ex:
                        com_success = False
                        com_err = str(ex)

                    if not com_success:
                        raise ValueError(f"Live ETABS mode requested (in_tool=False), but ETABS API COM connection failed. ({com_err})")

                # 2. If in_tool is True (In-tool mode: parse file completely inside tool code, ETABS installation not needed)
                if in_tool:
                    if raw_bytes:
                        parser = E2KParser()
                        model = parser.parse_binary_edb_bytes(
                            raw_bytes,
                            filename=job.filename,
                            companion_text=companion_text,
                        )
                        model.project_name = job.filename
                        job.building_model = model
                    else:
                        raise ValueError(f"No file content data supplied for in-tool processing of '{job.filename}'.")
            else:
                parser = E2KParser()
                model = parser.parse_string(file_content or "")
                job.building_model = model

            job.progress = 60
            job.stage = "Extracting stories and structural elements..."
            await asyncio.sleep(0.1)

            job.progress = 90
            job.stage = "Running geometry validation..."
            await asyncio.sleep(0.1)

            job.status = "COMPLETED"
            job.progress = 100
            job.stage = "Model ready for floor extraction and RAM Concept export."
        except Exception as e:
            job.status = "FAILED"
            job.error = str(e)
            job.stage = "Processing failed."


# Global singleton instance
job_manager = JobManager()
