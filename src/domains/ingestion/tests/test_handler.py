from ..domain.job import IngestionJob
from ..domain.stages import IngestionStage
from ..domain.failure import FailureReason, FailureKind
from ..api.commands import IngestDocument
from ..orchestration.handler import IngestionCommandHandler
from ..tests.fakes.fake_pipeline import FakePipeline
from ..tests.fakes.fake_job_repository import FakeJobRepository
from uuid import uuid4
import pytest


@pytest.fixture
def repo():
    return FakeJobRepository()

@pytest.fixture
def pipeline(repo):
    return FakePipeline()


@pytest.fixture
def handler(pipeline, repo):
    return IngestionCommandHandler(pipeline, repo)

def _make_complete_job(job: IngestionJob) -> None:
    if job.stage == IngestionStage.QUEUED:
        for stage in [
            IngestionStage.EXTRACTING,
            IngestionStage.CHUNKING,
            IngestionStage.EMBEDDING,
            IngestionStage.INDEXING,
            IngestionStage.COMPLETED,
        ]:
            job.advance_to(stage)

def _make_failed_job(kind: FailureKind) -> None:
    def behavior(job: IngestionJob) -> None:
        if job.stage == IngestionStage.QUEUED:
            job.advance_to(IngestionStage.EXTRACTING)
            job.mark_failed(FailureReason(
                kind=kind,
                message="Permanent failure",
                stage=IngestionStage.EXTRACTING,
            ))
    return behavior


class MakeFailedJob:
    def __init__(self, kind: FailureKind):
        self.kind = kind

    def __call__(self, job: IngestionJob) -> None:
        if job.stage == IngestionStage.QUEUED:
            job.advance_to(IngestionStage.EXTRACTING)
            job.mark_failed(FailureReason(
                kind=self.kind,
                message="Permanent failure",
                stage=IngestionStage.EXTRACTING,
            ))




def test_create_a_job_and_persitsts_it(handler, pipeline, repo):
    pipeline.behavior = _make_complete_job
    command = IngestDocument(
        document_id=uuid4(),
        source_location="test.pdf",
        mime_type="application/pdf",
    )
    handler.handle_ingest(command)
    job = repo.get_by_document(command.document_id)
    assert job is not None
    assert job.stage == IngestionStage.COMPLETED
    assert job.failure is None
    assert job.attempts == 1
    assert job.document_id == command.document_id
    
def test_job_ends_completed_when_pipeline_succeeds(handler, pipeline, repo):
    pipeline.behavior = _make_complete_job
    command = IngestDocument(
        document_id=uuid4(),
        source_location="test.pdf",
        mime_type="application/pdf",
    )
    handler.handle_ingest(command)
    job = repo.get_by_document(command.document_id)
    assert job.stage == IngestionStage.COMPLETED

def test_job_ends_failed_when_pipeline_fails(handler, pipeline, repo):
    pipeline.behavior = MakeFailedJob(FailureKind.PERMANENT)
    command = IngestDocument(
        document_id=uuid4(),
        source_location="test.pdf",
        mime_type="application/pdf",
    )
    handler.handle_ingest(command)
    job = repo.get_by_document(command.document_id)
    assert job.stage == IngestionStage.FAILED
    assert job.failure is not None
    assert job.failure.kind == FailureKind.PERMANENT


def test_does_not_retry(handler, pipeline, repo):
    pipeline.behavior = MakeFailedJob(FailureKind.PERMANENT)
    command = IngestDocument(
        document_id=uuid4(),
        source_location="test.pdf",
        mime_type="application/pdf",
    )
    handler.handle_ingest(command)
    assert pipeline.run_count == 1