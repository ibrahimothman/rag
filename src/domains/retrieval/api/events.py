from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class ChunkResult:
    chunk_id: UUID
    content: str
    score: float
    document_id: UUID
    page: int | None = None


@dataclass(frozen=True)
class RetrievalCompleted:
    """
    The event to signal the completion of a retrieval operation.
    """
    request_id: UUID
    retrieval_id: UUID
    query_text: str
    chunks: list[ChunkResult]
    chunk_count: int 
    duration_ms: int = 0


@dataclass(frozen=True)
class FailureReason:
    stage: str
    kind: str
    message: str

@dataclass(frozen=True)
class RetrievalFailed:
    """
    The event to signal the failure of a retrieval operation.
    """
    request_id: UUID
    retrieval_id: UUID
    query_text: str
    reason: FailureReason
    duration_ms: int = 0