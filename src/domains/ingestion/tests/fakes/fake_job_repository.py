from ...orchestration.job_repository import JobRepository, JobNotFoundError, JobRepositoryError
from ...domain.job import IngestionJob
from ...domain.stages import IngestionStage
from uuid import UUID

class FakeJobRepository(JobRepository):
    """
    In-memory implementation of JobRepository for testing purposes.
    """


    def __init__(self):
        self._jobs: dict[UUID, IngestionJob] = {}
    
    def save(self, job: IngestionJob) -> None:
        self._jobs[job.id] = job

    def get(self, job_id: UUID) -> IngestionJob:
        if job_id not in self._jobs:
            raise JobNotFoundError(f"Job not found: {job_id}")
        return self._jobs[job_id]

    
    def get_by_document(self, document_id: UUID) -> IngestionJob | None:
        for job in self._jobs.values():
            if job.document_id == document_id:
                return job
        return None

    
    def list_by_stage(self, stage: IngestionStage) -> list[IngestionJob]:
        return [job for job in self._jobs.values() if job.stage == stage]




