from platform import python_version_tuple
from .query import Query
from .chunk import ScoredChunk
from uuid import UUID
from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalResult:
    """
    The output of a complete retrieval operation.
    
    Carries the chunks found (if any), correlation IDs for tracing, and
    the original query text for downstream use (citations, logging,
    analytics).
    """
    request_id: UUID
    retrieval_id: UUID
    query: Query
    chunks: list[ScoredChunk]


    @property
    def chunk_count(self) -> int:
        return len(self.chunks)

    @property
    def is_empty(self) -> bool:
        return self.chunk_count == 0
