from ..api.commands import IngestDocument, ReingestDocument, RetryIngestion
from ..domain.job import IngestionJob, TERMINAL_STATES
from ..stages.extractor import SourceFile
from .pipeline import Pipeline
from .job_repository import JobRepository
from ..domain.exceptions import JobNotRetryable
from ..domain.stages import IngestionStage
import time

class IngestionHandler:

    
    def __init__(self, pipeline: Pipeline, jobs: JobRepository):
        self._pipeline = pipeline
        self._jobs = jobs

    def handle_ingest(self, command: IngestDocument) -> None:
        job = IngestionJob.create(command.document_id)
        self._jobs.save(job)
        self._run_pipeline(job, command)


    def handle_ingest_existing_job(self, job: IngestionJob, command: IngestDocument) -> None:
        self._run_pipeline(job, command)

    def handle_reingest(self, command: ReingestDocument) -> None:
        # ensure there is no running job for this document
        job = self._jobs.get_by_document(command.document_id)
        if job and job.satage not in TERMINAL_STATES:
            return # ignore if there is a running job

        # create a new job
        job = IngestionJob.create(command.document_id)
        self._jobs.save(job)
        self._run_pipeline(job, command)
   

    def handle_retry(self, command: RetryIngestion) -> None:
        job_id = command.job_id
        source = SourceFile(command.source_location, command.mime_type)
        job = self._jobs.get(job_id)
        
        try:
            job.retry()
        except JobNotRetryable as e:
            return

        self._jobs.save(job)
        self._pipeline.run(job, source)


    def _run_pipeline(self, job: IngestionJob, command) -> None:
        source = SourceFile(command.source_location, command.mime_type)
        self._pipeline.run(job, source)
        
        