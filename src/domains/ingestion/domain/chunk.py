from dataclasses import dataclass
from uuid import UUID

@dataclass(frozen=True)
class Chunk:
    id: UUID
    text: str
    source_document_id: UUID
    position: int
    chunking_strategy_version: str
    metadata: dict


@dataclass(frozen=True)
class EmbeddedChunk:
    chunk: Chunk
    vector: list[float]
    embedding_model_version: str




