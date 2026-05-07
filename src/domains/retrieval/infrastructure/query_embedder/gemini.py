from src.domains.retrieval.stages.query_embedder import (
    QueryEmbedder,
    QueryEmbeddingFailed
)
from src.domains.retrieval.domain.query import (
    Query, EmbeddedQuery
)
from google import genai
from google.genai import errors

from dataclasses import dataclass


@dataclass(frozen=True)
class GeminiQueryEmbedderConfig:
    model: str
    embedding_size: int
    api_key: str

class GeminiQueryEmbedder(QueryEmbedder):
    
    def __init__(self, config: GeminiQueryEmbedderConfig):
        self._config = config
        self._client = genai.Client(api_key=self._config.api_key)

    @property
    def model_version(self) -> str:
        return f"{self._config.model}@{self._config.embedding_size}"

    def embed(self, query: Query) -> EmbeddedQuery:
        return EmbeddedQuery(
            query=query, 
            vector=self._embed(query.text), 
            embedding_model_version=self.model_version
        )

    def _embed(self, query_text: str) -> list[float]:
        try:
            results = self._client.models.embed_content(
                model=self._config.model,
                contents=[self._format_query_for_embedding(query_text)],
                config={
                    "output_dimensionality": self._config.embedding_size
                }
            )
            if not results or not results.embeddings or not results.embeddings[0] or not results.embeddings[0].values:
                raise QueryEmbeddingFailed(f"Embedding API returned empty results", permanent=True)
            return results.embeddings[0].values
        except errors.ClientError as e:
            # ClientError: If the status code is in the 4xx range.
            # 429 (rate limit and quota exceeded)
            if e.code == 429:
                raise QueryEmbeddingFailed(f"Rate limited: {e}", permanent=False)
            raise QueryEmbeddingFailed(f"Client error: {e}", permanent=True)

        except errors.ServerError as e:
            # ServerError: If the status code is in the 5xx range.
            # 503 (DEADLINE_EXCEEDED), could be due to the prompt is too long or the server is overloaded,
            # better to retry, any way the policy retry governs by limiting the number of retries
            if e.code == 503:
                raise QueryEmbeddingFailed(f"Service unavailable: {e}", permanent=False)
            raise QueryEmbeddingFailed(f"Server error: {e}", permanent=True)

        except errors.APIError as e:
            # for other errors
            raise QueryEmbeddingFailed(f"API error: {e}", permanent=True)

    @classmethod
    def _format_query_for_embedding(cls, query_text: str) -> str:
        return f"task: question answering | query: {query_text}"