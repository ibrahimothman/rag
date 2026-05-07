from abc import ABC, abstractmethod
from uuid import UUID
from ..domain.job import IngestionJob
from ..domain.stages import IngestionStage

class JobRepository(ABC):

    @abstractmethod
    def save(self, job: IngestionJob) -> None:
        """Save the job to the repository"""

    @abstractmethod
    def get(self, job_id: UUID) -> IngestionJob:
        """Get the job from the repository"""

    @abstractmethod
    def get_by_document(self, document_id: UUID) -> IngestionJob | None:
        """Delete the job from the repository"""

    @abstractmethod
    def list_by_stage(self, stage: IngestionStage) -> list[IngestionJob]:
        """List the jobs by status"""



class JobRepositoryError(Exception):
    def __init__(self, message: str, permanent: bool):
        self.message = message
        self.permanent = permanent

class JobNotFoundError(Exception):
    """Raised by get() when a job_id is not found"""
