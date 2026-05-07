from abc import ABC, abstractmethod
from src.domains.retrieval.domain.query import Query, EmbeddedQuery

class QueryEmbedder(ABC):
    """
    A stage that embeds queries.
    """
    @property
    @abstractmethod
    def model_version(self) -> str:
        """The version of the embedding model"""

    @abstractmethod
    def embed(self, query: Query) -> EmbeddedQuery:
        """Produce an embedded query. May raise QueryEmbeddingFailed (transient or permanent)"""

class QueryEmbeddingFailed(Exception):
    def __init__(self, message: str, permanent: bool):
        super().__init__(message)
        self.message = message
        self.permanent = permanent