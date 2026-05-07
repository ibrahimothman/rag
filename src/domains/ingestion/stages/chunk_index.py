from abc import ABC, abstractmethod
from uuid import UUID
from ..domain.chunk import EmbeddedChunk


class ChunkIndex(ABC):
    """
    A place where the processed content (chunks and embeddings) is stored
    so it can later be retrieved and used for downstream features
    """

    @abstractmethod
    async def write_for_document(self, document_id: UUID, chunks: list[EmbeddedChunk]) -> None:
        """Replace all chunks belong to the document with the new ones"""

    @abstractmethod
    async def remove_for_document(self, document_id: UUID) -> None:
        """Remove all chunks belong to the document"""


class IndexingFailed(Exception):
    """Raised when indexing fails"""
    def __init__(self, message: str, permanent: bool):
        self.message = message
        self.permanent = permanent
