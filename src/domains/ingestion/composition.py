from .infrastructure.extractor import PdfExtractor, PlainTextExtractor
from .infrastructure.chunker import FixedSizeChunker, FixedSizeChunkerConfig
from .infrastructure.embedder import GeminiEmbedder, GeminiEmbedderConfig
from .infrastructure.chunk_index import PgVectorChunkIndex, PgVectorChunkIndexConfig
from .infrastructure.job_repostiory import PostgresJobRepository, PostgresJobRepositoryConfig
from src.shared.event_publishers import InMemoryEventPublisher
from src.shared.gemini import GeminiProviderClient, GeminiProviderClientConfig
from .orchestration.pipeline import Pipeline
from .orchestration.handler import IngestionHandler
from .orchestration.retrying_handler import RetryingIngestionHandler
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

    gemini_provider_client = GeminiProviderClient(
        GeminiProviderClientConfig(
            api_key=config.gemini_api_key,
        )
    )

    embedder = GeminiEmbedder(GeminiEmbedderConfig(
        model=config.embedding_model,
        embedding_size=config.embedding_size
    ), gemini_provider_client)

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
        embedder=embedder,
        chunk_index=chunk_index,
        jobs=jobs,
        events=event_publisher,
    )

    handler = IngestionHandler(pipeline, jobs)
    retrying_handler = RetryingIngestionHandler(handler, jobs)
    return retrying_handler



