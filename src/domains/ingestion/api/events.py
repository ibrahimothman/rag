from uuid import UUID
from datetime import datetime
from dataclasses import dataclass


@dataclass(frozen=True)
class IngestionStarted:
    document_id: UUID
    job_id: UUID
    started_at: datetime


@dataclass(frozen=True)
class DocumentIndexed:    
    document_id: UUID
    job_id: UUID
    chunk_count: int
    indexed_at: datetime


@dataclass(frozen=True)
class FailureReason:
    stage: str
    kind: str
    message: str

@dataclass(frozen=True)
class IngestionFailed:
    document_id: UUID
    job_id: UUID
    failure_reason: FailureReason
    failed_at: datetime

