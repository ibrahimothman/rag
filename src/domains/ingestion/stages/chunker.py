from abc import ABC, abstractmethod
from ..domain.chunk import Chunk
from .extractor import ExtractedDocument


class Chunker(ABC):
    """
    A something that can take the document content and prouduce a sequence of text chunks
    suitable for the downstream processing
    """

    @property
    @abstractmethod
    def strategy_version(self) -> str:
        """The version of the chunking strategy"""
    
    
    @abstractmethod
    def chunk(self, document: ExtractedDocument) -> list[Chunk]:
        """Produce chunks. Should be deterministic for the same input."""