from ..domain.job import IngestionJob
from ..domain.stages import IngestionStage
from ..domain.failure import FailureReason, FailureKind
from ..api.commands import IngestDocument
from ..orchestration.handler import IngestionCommandHandler
from ..tests.fakes.fake_pipeline import FakePipeline
from ..tests.fakes.fake_job_repository import FakeJobRepository
from ..orchestration.retrying_handler import RetryingIngestionCommandHandler
from uuid import uuid4
import pytest
from unittest.mock import patch



class FakeIngestionCommandHandler:

    def __init__(self, jobs, behaviors: list):
        self._jobs = jobs
        self._behaviors = behaviors
        self.run_count = 0
        

    def handle_ingest(self, command) -> None:
        job = IngestionJob.create(command.document_id)
        self._jobs.save(job)

        self._apply_next_behavior(job)

    def handle_ingest_existing_job(self, job, command) -> None:
        self._apply_next_behavior(job)
    
    def _apply_next_behavior(self, job) -> None:
        if not self._behaviors:
            return
        
        self.run_count += 1
        behavior = self._behaviors.pop(0)
        behavior(job)
        self._jobs.save(job)

        

    



@pytest.fixture
def repo():
    return FakeJobRepository()

@pytest.fixture(autouse=True)
def no_sleep():
    """Prevent actual sleeping during tests."""
    with patch("time.sleep"):
        yield    




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



def test_no_retry_when_pipeline_succeeds(repo):
    behaviors = [_make_complete_job]
    inner = FakeIngestionCommandHandler(repo, behaviors)
    handler = RetryingIngestionCommandHandler(inner=inner, jobs=repo)
    command = IngestDocument(
        document_id=uuid4(),
        source_location="test.pdf",
        mime_type="application/pdf",
    )
    handler.handle_ingest(command)
    job = repo.get_by_document(command.document_id)
    assert job.stage == IngestionStage.COMPLETED
    assert inner.run_count == 1


def test_no_retry_on_permanent_failure(repo):
    behaviors = [_make_failed_job(FailureKind.PERMANENT)]
    inner = FakeIngestionCommandHandler(repo, behaviors)
    handler = RetryingIngestionCommandHandler(inner=inner, jobs=repo)
    command = IngestDocument(
        document_id=uuid4(),
        source_location="test.pdf",
        mime_type="application/pdf",
    )
    handler.handle_ingest(command)
    job = repo.get_by_document(command.document_id)
    assert job.stage == IngestionStage.FAILED
    assert inner.run_count == 1
    assert job.attempts == 1


def test_retry_on_transient_failure_untill_success(repo):
    behaviors = [
        _make_failed_job(FailureKind.TRANSIENT),
        _make_failed_job(FailureKind.TRANSIENT),
        _make_complete_job,
    ]
    inner = FakeIngestionCommandHandler(repo, behaviors)
    handler = RetryingIngestionCommandHandler(inner=inner, jobs=repo)
    command = IngestDocument(
        document_id=uuid4(),
        source_location="test.pdf",
        mime_type="application/pdf",
    )
    handler.handle_ingest(command)
    job = repo.get_by_document(command.document_id)
    assert job.stage == IngestionStage.COMPLETED
    assert inner.run_count == 3
    assert job.attempts == 3


def test_stops_after_exhausting_max_attempts(repo):
    behaviors = [
        _make_failed_job(FailureKind.TRANSIENT),
        _make_failed_job(FailureKind.TRANSIENT),
        _make_failed_job(FailureKind.TRANSIENT),
        _make_complete_job
    ]
    inner = FakeIngestionCommandHandler(repo, behaviors)
    handler = RetryingIngestionCommandHandler(inner=inner, jobs=repo)
    command = IngestDocument(
        document_id=uuid4(),
        source_location="test.pdf",
        mime_type="application/pdf",
    )
    handler.handle_ingest(command)
    job = repo.get_by_document(command.document_id)
    assert job.stage == IngestionStage.FAILED
    assert inner.run_count == 3
    assert job.attempts == 3


def test_sleep_is_called_between_attempts(repo):
    behaviors = [
        _make_failed_job(FailureKind.TRANSIENT),
        _make_failed_job(FailureKind.TRANSIENT),
        _make_complete_job,
    ]
    inner = FakeIngestionCommandHandler(repo, behaviors)
    handler = RetryingIngestionCommandHandler(inner=inner, jobs=repo)
    command = IngestDocument(
        document_id=uuid4(),
        source_location="test.pdf",
        mime_type="application/pdf",
    )

    with patch("time.sleep") as mock_sleep:
        handler.handle_ingest(command)

    assert mock_sleep.call_count == 2

def test_succeeds_immediately_if_job_is_already_completed(repo):
    behaviors = [_make_complete_job]
    inner = FakeIngestionCommandHandler(repo, behaviors)
    handler = RetryingIngestionCommandHandler(inner=inner, jobs=repo)
    command = IngestDocument(
        document_id=uuid4(),
        source_location="test.pdf",
        mime_type="application/pdf",
    )

    with patch("time.sleep") as mock_sleep:
        handler.handle_ingest(command)

    assert mock_sleep.call_count == 0
    


    