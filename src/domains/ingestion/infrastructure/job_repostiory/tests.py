import pytest
import psycopg
from .postgres_job_repository import PostgresJobRepository, PostgresJobRepostioryConfig
from ...orchestration.job_repository import JobNotFoundError, JobRepositoryError
from ...domain.job import IngestionJob
from ...domain.stages import IngestionStage
from ...domain.failure import RetryPolicy, FailureReason, FailureKind

from uuid import uuid4

TEST_DB_URL = "postgresql://postgres:postgres@localhost:5432/rag-app"

@pytest.fixture
def repo():
    config = PostgresJobRepostioryConfig(db_url=TEST_DB_URL)
    return PostgresJobRepository(config)

@pytest.fixture(autouse=True)
def cleanup():
    with psycopg.connect(TEST_DB_URL) as conn:
        conn.execute("TRUNCATE TABLE ingestion_jobs")
    yield

def test_save_new_job(repo):
    job = IngestionJob.create(document_id=uuid4())
    repo.save(job)
    saved = repo.get(job.id)
    assert saved.id == job.id


def test_save_updates_existing_job(repo):
    job = IngestionJob.create(document_id=uuid4())
    repo.save(job)
    job.advance_to(IngestionStage.EXTRACTING)
    repo.save(job)
    saved = repo.get(job.id)
    assert saved.stage == IngestionStage.EXTRACTING

def test_get_missing_raises_error(repo):
    with pytest.raises(JobNotFoundError):
        repo.get(uuid4())

def test_get_by_document_returns_none_if_missing(repo):
    assert repo.get_by_document(uuid4()) is None

def test_get_by_document_returns_job_if_found(repo):
    job = IngestionJob.create(document_id=uuid4())
    repo.save(job)
    saved = repo.get_by_document(job.document_id)
    assert saved is not None
    assert saved.id == job.id
   

def test_duplicate_document_id_fails(repo):
    document_id = uuid4()
    job = IngestionJob.create(document_id=document_id)
    job2 = IngestionJob.create(document_id=document_id)
    
    repo.save(job)
    with pytest.raises(JobRepositoryError) as e:
        repo.save(job2)

    assert e.value.permanent is True


def test_list_by_statge(repo):
    queued = IngestionJob.create(document_id=uuid4())
    repo.save(queued)

    running = IngestionJob.create(document_id=uuid4())
    running.advance_to(IngestionStage.EXTRACTING)
    repo.save(running)

    queued_jobs = repo.list_by_stage(IngestionStage.QUEUED)
    assert len(queued_jobs) == 1
    assert queued_jobs[0].id == queued.id

def test_save_preserve_failure(repo):
    job = IngestionJob.create(document_id=uuid4())
    job.advance_to(IngestionStage.EXTRACTING)
    job.mark_failed(FailureReason(
        kind=FailureKind.PERMANENT, 
        message="Corrupt PDF", 
        stage=IngestionStage.EXTRACTING)
    )
    repo.save(job)
    saved = repo.get(job.id)
    assert saved.failure is not None
    assert saved.failure.kind == FailureKind.PERMANENT
    assert saved.failure.message == "Corrupt PDF"
    assert saved.failure.stage == IngestionStage.EXTRACTING
    
