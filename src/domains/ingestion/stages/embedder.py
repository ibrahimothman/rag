from abc import ABC, abstractmethod
from ..domain.chunk import Chunk, EmbeddedChunk

class Embedder(ABC):
    """
    A something that can turn pieces of texts into vectors
    suitable for similarity-search retrieval
    """

    
    @property
    @abstractmethod
    def model_version(self) -> str:
        """The version of the embedding model"""
    
    @abstractmethod
    def embed(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
        """Embed chunks. May raise EmbeddingFailed (transient or permanent)"""

class EmbeddingFailed(Exception):
    def __init__(self, message: str, permanent: bool):
        self.message = message
        self.permanent = permanent