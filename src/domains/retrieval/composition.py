from dataclasses import dataclass

from src.domains.retrieval.infrastructure.query_embedder.gemini import (
    GeminiQueryEmbedder, GeminiQueryEmbedderConfig
)

from src.domains.retrieval.infrastructure.chunk_search.pgvector import (
    PgVectorChunkSearch, 
    PgVectorChunkSearchConfig
)

from src.domains.retrieval.infrastructure import InMemoryEventPublisher

from src.domains.retrieval.orchestration.handler import RetrievalHandler

from src.domains.retrieval.orchestration.pipeline import RetrievalPipeline

@dataclass(frozen=True)
class RetrievalConfig:
    """Configuration for the retrieval system"""
    # Database
    db_url: str

    # Embedding
    gemini_api_key: str
    embedding_model: str
    embedding_size: int
   
    

def build_retrieval(
    config: RetrievalConfig,
    event_subscribers: list | None = None,
):

   
    query_embedder = GeminiQueryEmbedder(GeminiQueryEmbedderConfig(
        model=config.embedding_model,
        embedding_size=config.embedding_size,
        api_key=config.gemini_api_key,
    ))

    chunk_search = PgVectorChunkSearch(PgVectorChunkSearchConfig(
        db_url=config.db_url,
    ))


    event_publisher = InMemoryEventPublisher(
        subscribers=event_subscribers or [],
    )

    pipeline = RetrievalPipeline(
        query_embedder=query_embedder,
        chunk_search=chunk_search,
        events=event_publisher
    )

    handler = RetrievalHandler(pipeline)
    return handler



