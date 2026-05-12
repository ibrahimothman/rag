from .handler import IngestionHandler
from ..api.commands import IngestDocument
from ..domain.exceptions import JobNotRetryable
from .job_repository import JobRepository
from ..domain.stages import IngestionStage
import time
import logging

logger = logging.getLogger("ingestion.retry")

class RetryingIngestionHandler:
    def __init__(self, inner: IngestionHandler, jobs: JobRepository):
        self._inner = inner
        self._jobs = jobs

    def handle_ingest(self, command: IngestDocument) -> None:
        self._inner.handle_ingest(command)

        while True:
            job = self._jobs.get_by_document(command.document_id)
            if job is None or job.stage == IngestionStage.COMPLETED:
                return
            try:
                job.retry()
                self._jobs.save(job)
            except JobNotRetryable as e:
                return

            logger.info(
                f"Retrying job {job.id} (attempt {job.attempts}) after "
                f"{job.retry_policy.backoff_seconds}s backoff"
            )    
            time.sleep(job.retry_policy.backoff_seconds)
            self._inner.handle_ingest_existing_job(job, command)
