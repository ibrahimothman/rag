import stat
from ...orchestration.job_repository import JobRepository, JobNotFoundError, JobRepositoryError
from ...domain.job import IngestionJob
from ...domain.stages import IngestionStage
from ...domain.failure import FailureReason, FailureKind, RetryPolicy

from dataclasses import asdict, dataclass
from uuid import UUID
import psycopg
from psycopg.errors import (
    OperationalError,
    InterfaceError,
    UndefinedTable,
    UndefinedColumn,
    IntegrityError,
    DataError
)
from psycopg.rows import dict_row
from psycopg.types.json import Json


@dataclass(frozen=True)
class PostgresJobRepositoryConfig:
    db_url: str

class PostgresJobRepository(JobRepository):

    """
    Stores IngestionJobs in PostgreSQL.
    
    save() upserts by job ID. get() raises JobNotFoundError if missing.
    get_by_document() returns None if no job exists for the document.
    list_by_status() returns all jobs in a given stage.
    """

    def __init__(self, config: PostgresJobRepositoryConfig):
        self._config = config

    def save(self, job: IngestionJob) -> None:  
        try:
            with psycopg.connect(self._config.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO ingestion_jobs (
                            id, document_id, stage, attempts, failure, retry_policy, started_at, updated_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                        stage = EXCLUDED.stage,
                        attempts = EXCLUDED.attempts,
                        failure = EXCLUDED.failure,
                        updated_at = EXCLUDED.updated_at
                        """,
                        (
                            job.id, 
                            job.document_id, 
                            job.stage.value, 
                            job.attempts, 
                            Json(self._failure_to_json(job.failure)) if job.failure else None, 
                            Json(self._retry_policy_to_json(job.retry_policy)) if job.retry_policy else None, 
                            job.started_at, 
                            job.updated_at
                        )
                    )
        except (OperationalError, InterfaceError) as e:
            raise JobRepositoryError(f"Database connection error: {e}", permanent=False)
        except (UndefinedTable, UndefinedColumn) as e:
            raise JobRepositoryError(f"Database schema error: {e}", permanent=True)
        except IntegrityError as e:
            raise JobRepositoryError(f"Integrity violation  : {e}", permanent=True)
        except DataError as e:
            raise JobRepositoryError(f"Data error: {e}", permanent=True)

    def get(self, job_id: UUID) -> IngestionJob:
       
        row = self._fetch_one(
            """
            SELECT id, document_id, stage, attempts, failure,
                retry_policy, started_at, updated_at
            FROM ingestion_jobs WHERE id = %s
            """,
            (job_id,)
        )

        if row is None:
            raise JobNotFoundError(f"Job not found: {job_id}")
        return self._row_to_job(row)    
        

    def get_by_document(self, document_id: UUID) -> IngestionJob | None:
        row = self._fetch_one(
            """
            SELECT id, document_id, stage, attempts, failure,
                retry_policy, started_at, updated_at
            FROM ingestion_jobs WHERE document_id = %s
            """,
            (document_id,)
        )
        return self._row_to_job(row) if row else None

    def list_by_stage(self, stage: IngestionStage) -> list[IngestionJob]:
        rows = self._fetch_all(
            """
            SELECT id, document_id, stage, attempts, failure,
                retry_policy, started_at, updated_at
            FROM ingestion_jobs WHERE stage = %s
            """,
            (stage.value,)
        )
        return [self._row_to_job(row) for row in rows]


    # ----- Read helpers -----
    def _fetch_one(self, sql: str, params: tuple) -> dict | None:
        try:
            with psycopg.connect(self._config.db_url) as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute(sql, params)
                    return cur.fetchone()
        except (OperationalError, InterfaceError) as e:
            raise JobRepositoryError(f"Database connection error: {e}", permanent=False)
        except (UndefinedTable, UndefinedColumn) as e:
            raise JobRepositoryError(f"Schema error: {e}", permanent=True)

    def _fetch_all(self, sql: str, params: tuple) -> list[dict]:
        try:
            with psycopg.connect(self._config.db_url) as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute(sql, params)
                    return cur.fetchall()
        except (OperationalError, InterfaceError) as e:
            raise JobRepositoryError(f"Database connection error: {e}", permanent=False)
        except (UndefinedTable, UndefinedColumn) as e:
            raise JobRepositoryError(f"Schema error: {e}", permanent=True)  


    # ----- Domain/row mapping ---------------------
    def _row_to_job(self, row: dict) -> IngestionJob:
        return IngestionJob(
            id=row["id"],
            document_id=row["document_id"],
            stage=IngestionStage(row["stage"]),
            attempts=row["attempts"],
            failure=self._failure_from_json(row["failure"]),
            retry_policy=self._retry_policy_from_json(row["retry_policy"]),
            started_at=row["started_at"],
            updated_at=row["updated_at"]
        )

    @staticmethod
    def _failure_from_json(json: dict | None) -> FailureReason | None:
        if json is None:
            return None
        return FailureReason(
            kind=FailureKind(json["kind"]),
            message=json["message"],
            stage=IngestionStage(json["stage"])
        )

    @staticmethod
    def _failure_to_json(failure: FailureReason | None) -> dict | None:
        if failure is None:
            return None
        return {
            "kind": failure.kind.value,
            "message": failure.message,
            "stage": failure.stage.value
        }

    @staticmethod
    def _retry_policy_from_json(json: dict | None) -> RetryPolicy:
        if json is None:
            return RetryPolicy.default()
        return RetryPolicy(
            max_attempts=json["max_attempts"],
            backoff_seconds=json["backoff_seconds"]
        )

    @staticmethod
    def _retry_policy_to_json(retry_policy: RetryPolicy) -> dict:
        return {
            "max_attempts": retry_policy.max_attempts,
            "backoff_seconds": retry_policy.backoff_seconds
        }
