from abc import ABC, abstractmethod
from src.domains.retrieval.domain.query import EmbeddedQuery
from src.domains.retrieval.domain.chunk import ScoredChunk

class ChunkSearch(ABC):
    """
    A stage that searches for relevant chunks.
    """

    @abstractmethod
    def find_similar_chunks(
        self, 
        query: EmbeddedQuery,
        limit: int
    ) -> list[ScoredChunk]:

        """
        Retrurn up to top_k chunks that are most similar to the query.

        Return an empty list if no chunks are found.

        Raises ChunkSearchFailed (transient or permanent) if the search fails (DB unreacahble, schema error, etc.)
        """

class ChunkSearchFailed(Exception):
    def __init__(self, message: str, permanent: bool):
        super().__init__(message)
        self.message = message
        self.permanent = permanent