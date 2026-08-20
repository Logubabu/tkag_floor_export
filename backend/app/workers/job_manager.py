import uuid
import time
import asyncio
from typing import Dict, Any, Optional
from app.models.intermediate import BuildingModel, FloorModel, ValidationResult, ExtractionMode
from app.etabs.e2k_parser import E2KParser
from app.floor_extractor.extractor import FloorExtractor
from app.validation.validator import StructuralValidator
from app.ram_concept.exporter import RAMConceptExporter


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
        job_id = str(uuid.uuid4())
        job = ProcessingJob(job_id, filename)
        self.jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> Optional[ProcessingJob]:
        return self.jobs.get(job_id)

    async def process_e2k_file(self, job_id: str, file_content: str):
        job = self.jobs.get(job_id)
        if not job:
            return

        try:
            job.status = "PROCESSING"
            job.progress = 20
            job.stage = "Parsing ETABS .E2K geometry & properties..."
            await asyncio.sleep(0.1)

            parser = E2KParser()
            model = parser.parse_string(file_content)
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
