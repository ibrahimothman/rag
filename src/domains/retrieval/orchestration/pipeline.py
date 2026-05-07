from src.domains.retrieval.infrastructure.query_embedder.gemini import QueryEmbedder, QueryEmbeddingFailed
from src.domains.retrieval.infrastructure.chunk_search.pgvector import ChunkSearch, ChunkSearchFailed
from src.domains.retrieval.domain.result import RetrievalResult 
from src.domains.retrieval.domain.query import Query, EmbeddedQuery
from src.domains.retrieval.domain.chunk import ScoredChunk
from src.domains.retrieval.domain.failure import (
    FailureReason as DomainFailureReason, 
    FailureKind as DomainFailureKind
)
from src.domains.retrieval.orchestration.event_publisher import EventPublisher
from src.domains.retrieval.api.events import (
    RetrievalFailed, 
    RetrievalCompleted, 
    ChunkResult, 
    FailureReason as ApiFailureReason
)
from uuid import UUID, uuid4

class RetrievalPipeline:

    def __init__(
        self, 
        query_embedder: QueryEmbedder, 
        chunk_search: ChunkSearch,
        events: EventPublisher,
        top_k: int = 2,
    ):
        self._query_embedder = query_embedder
        self._chunk_search = chunk_search
        self._events = events
        self._top_k = top_k
    

    def run(self, request_id: UUID, query_text: str) -> RetrievalResult | None:
        retrieval_id = uuid4()
        query = Query(text=query_text)
        try:
            embedded_query = self._embed_query(query)
            scored_chunks = self._find_similar_chunks(embedded_query, self._top_k * 2)
            top_chunks = scored_chunks[:self._top_k]

            result = RetrievalResult(
                request_id=request_id,
                retrieval_id=retrieval_id,
                query=query,
                chunks=top_chunks,
            )

            self._events.publish(RetrievalCompleted(
                request_id=request_id,
                retrieval_id=retrieval_id,
                query_text=query_text,
                chunks=[self._to_chunk_result(chunk) for chunk in top_chunks],
                chunk_count=len(top_chunks)
            ))
            
            return result

        except _StageFailure as f:
           self._record_failure(
            request_id=request_id,
            retrieval_id=retrieval_id,
            query_text=query_text,
            domain_failure=f.domain_failure
           )

        return None

    # ------- Stage methods ------------------------

    def _embed_query(self, query: Query) -> EmbeddedQuery:
        try:
            return self._query_embedder.embed(query)
        except QueryEmbeddingFailed as e:
            raise _StageFailure(DomainFailureReason(
                kind=DomainFailureKind.PERMANENT if e.permanent else DomainFailureKind.TRANSIENT,
                message=e.message,
                stage="query_embedding")
            )

    def _find_similar_chunks(self, embedded_query: EmbeddedQuery, limit: int) -> list[ScoredChunk]:
        try:
            return self._chunk_search.find_similar_chunks(embedded_query, limit)
        except ChunkSearchFailed as e:
            raise _StageFailure(DomainFailureReason(
                kind=DomainFailureKind.PERMANENT if e.permanent else DomainFailureKind.TRANSIENT,
                message=e.message,
                stage="chunk_search")
            )

    def _record_failure(self, request_id: UUID, retrieval_id: UUID, query_text: str, domain_failure: DomainFailureReason) -> None:
        self._events.publish(RetrievalFailed(
            request_id=request_id,
            retrieval_id=retrieval_id,
            query_text=query_text,
            reason=self._to_api_failure_reason(domain_failure)
        ))   



    # ------- Translation helpers ------------------------------------------------------------------
    @staticmethod
    def _to_chunk_result(scored_chunk: ScoredChunk) -> ChunkResult:
        return ChunkResult(
            chunk_id=scored_chunk.chunk_id,
            content=scored_chunk.content,
            score=scored_chunk.score,
            document_id=scored_chunk.citation.document_id,
            page=scored_chunk.citation.page,
        )


    @staticmethod
    def _to_api_failure_reason(domain_failure: DomainFailureReason) -> ApiFailureReason:
        return ApiFailureReason(
            stage=domain_failure.stage,
            kind=domain_failure.kind.value,
            message=domain_failure.message,
        )      

    
    

class _StageFailure(Exception):
    def __init__(self, domain_failure: DomainFailureReason):
        self.domain_failure = domain_failure

           

            