from .infrastructure.extractor import PdfExtractor, PlainTextExtractor
from .infrastructure.chunker import FixedSizeChunker, FixedSizeChunkerConfig
from .infrastructure.embedder import GeminiEmbedder, GeminiEmbedderConfig
from .infrastructure.chunk_index import PgVectorChunkIndex, PgVectorChunkIndexConfig
from .infrastructure.job_repostiory import PostgresJobRepository, PostgresJobRepositoryConfig
from .infrastructure.event_publisher import InMemoryEventPublisher
from .orchestration.pipeline import Pipeline
from .orchestration.handler import IngestionCommandHandler
from .observability.logging_subscriber import log_event
from src.scripts.flaky_embedder import FlakyEmbedder
from .orchestration.retrying_handler import RetryingIngestionCommandHandler
from dataclasses import dataclass

@dataclass(frozen=True)
class IngestionConfig:
    """Configuration for the ingestion system"""
    # Database
    db_url: str

    # Embedding
    gemini_api_key: str
    embedding_model: str
    embedding_size: int
    # Chunker
    chunk_size: int
    overlap_size: int

    

def build_ingestion(
    config: IngestionConfig,
    event_subscribers: list | None = None,
):

    extractors = [PdfExtractor(), PlainTextExtractor()]

    chunker = FixedSizeChunker(FixedSizeChunkerConfig(
        chunk_size=config.chunk_size,
        overlap_size=config.overlap_size,
    ))

    embedder = GeminiEmbedder(GeminiEmbedderConfig(
        model=config.embedding_model,
        embedding_size=config.embedding_size,
        api_key=config.gemini_api_key,
    ))

    flaky_embedder = FlakyEmbedder(embedder, fail_count=0)

    chunk_index = PgVectorChunkIndex(PgVectorChunkIndexConfig(
        db_url=config.db_url,
    ))

    jobs = PostgresJobRepository(PostgresJobRepositoryConfig(
        db_url=config.db_url,
    ))

    event_publisher = InMemoryEventPublisher(
        subscribers=event_subscribers or [],
    )

    pipeline = Pipeline(
        extractors=extractors,
        chunker=chunker,
        embedder=flaky_embedder,
        chunk_index=chunk_index,
        jobs=jobs,
        events=event_publisher,
    )

    handler = IngestionCommandHandler(pipeline, jobs)
    retrying_handler = RetryingIngestionCommandHandler(handler, jobs)
    return retrying_handler



