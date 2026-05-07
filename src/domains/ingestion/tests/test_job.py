from ..domain.job import IngestionJob
from ..domain.stages import IngestionStage
from ..domain.exceptions import IlligalStageTransition, JobNotRetryable
from ..domain.failure import FailureReason, FailureKind

from uuid import uuid4
import pytest

def test_advance_follows_pipeline_order():
    job = IngestionJob.create(document_id=uuid4())
    job.advance_to(IngestionStage.EXTRACTING)
    assert job.stage == IngestionStage.EXTRACTING


def test_cannot_skip_stages():
    job = IngestionJob.create(document_id=uuid4())
    with pytest.raises(IlligalStageTransition):
        job.advance_to(IngestionStage.INDEXING)


def tests_retry_resumes_from_failed_stage():
    job = IngestionJob.create(document_id=uuid4())
    job.advance_to(IngestionStage.EXTRACTING)
    job.advance_to(IngestionStage.CHUNKING)
    job.mark_failed(FailureReason(kind=FailureKind.TRANSIENT, message="Chunking failed", stage=IngestionStage.CHUNKING))
    job.retry()
    assert job.stage == IngestionStage.CHUNKING
    assert job.attempts == 2
    assert job.failure is None

def test_cannot_retry_permemnant_failures():
    job = IngestionJob.create(document_id=uuid4())
    job.advance_to(IngestionStage.EXTRACTING)
    job.mark_failed(FailureReason(kind=FailureKind.PERMANENT, message="Corrupt PDF", stage=IngestionStage.EXTRACTING))
    with pytest.raises(JobNotRetryable):
        job.retry()
  