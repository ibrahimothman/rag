from ...stages.chunker import Chunker
from ...domain.chunk import Chunk
from ...stages.extractor import ExtractedDocument

from dataclasses import dataclass
from uuid import uuid4


@dataclass(frozen=True)
class FixedSizeChunkerConfig:
    chunk_size: int
    overlap_size: int

class FixedSizeChunker(Chunker):

    """
    Splits text into fixed-character-size chunks with configurable overlap.
    
    A simple, deterministic strategy: walks the text in steps of (chunk_size - overlap)
    and emits a chunk of length chunk_size at each position. Overlap helps retrieval
    quality by ensuring concepts spanning a boundary appear in at least one chunk fully.
    """

    _STRATEGY_VERSION = "fixed_size_v1"
    
    def __init__(self, config: FixedSizeChunkerConfig | None = None):
        self._config = config or FixedSizeChunkerConfig()
        if self._config.overlap_size >= self._config.chunk_size:
            raise ValueError("Overlap size must be smaller than chunk size")

    
    @property
    def strategy_version(self) -> str:
        return f"{self._STRATEGY_VERSION}-{self._config.chunk_size}-{self._config.overlap_size}"
    
    def chunk(self, document: ExtractedDocument) -> list[Chunk]:
        chunks:list[Chunk] = []
        size = self._config.chunk_size
        step = size - self._config.overlap_size
        text_len = len(document.text)
        position = 0
        index = 0

        if text_len == 0:
            return []

        
        while position < text_len:
            end = min(position + size, text_len)
            chunk_text = document.text[position:end]
            chunks.append(Chunk(
                id=uuid4(),
                text=chunk_text,
                source_document_id=document.id,
                position=index,
                chunking_strategy_version=self.strategy_version,
                metadata={"char_start": position, "char_end": end}
            ))

            if end == text_len:
                break
            
            position += step
            index += 1

        return chunks