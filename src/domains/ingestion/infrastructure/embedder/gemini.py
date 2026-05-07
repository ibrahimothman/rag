from ipaddress import v6_int_to_packed
from multiprocessing import AuthenticationError
from src.domains.ingestion.stages.embedder import Embedder, EmbeddingFailed
from src.domains.ingestion.domain.chunk import Chunk, EmbeddedChunk
from dataclasses import dataclass
from google import genai
from google.genai import types, errors

from google.genai import types


# TODO:
# - retry and cache proxies
# - control the emebedding size, by default it's 3072 for gemini-embedding-2
# - error handling (rate limits, timeouts, connection errors, auth errors, malformed requests)
# - make it async

@dataclass(frozen=True)
class GeminiEmbedderConfig:
    embedding_size: int
    model: str
    api_key: str
    batch_size: int = 100

class GeminiEmbedder(Embedder):
    
    """
    Embeds chunks using Google Gemini's embeddings API.
    
    Sends chunks in batches to limit API call count. Classifies failures:
    rate limits, timeouts, and connection errors are transient (retry-worthy);
    auth errors and malformed requests are permanent.
    """
    
    def __init__(self, config: GeminiEmbedderConfig):
        self._config = config or GeminiEmbedderConfig()
        self._client = genai.Client(api_key=self._config.api_key)

    @property
    def model_version(self) -> str:
        return f"{self._config.model}@{self._config.embedding_size}"
    
    def embed(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
        if not chunks:
            return []

        embedded: list[EmbeddedChunk] = []

        for batch in self._batch(chunks):
            vectors = self._embed_batch(batch)
            for chunk, vector in zip(batch, vectors):
                embedded.append(EmbeddedChunk(
                    chunk=chunk, vector=vector,
                    embedding_model_version=self.model_version,
                ))
       
        return embedded

    def _batch(self, chunks: list[Chunk]):
        for i in range(0, len(chunks), self._config.batch_size):
            yield chunks[i:i + self._config.batch_size]

    def _embed_batch(self, batch: list[Chunk]) -> list[list[float]]:
        contents = [
            types.Content(
                parts=[
                    types.Part.from_text(text=self._apply_task(chunk.text))
                ]
            )
            for chunk in batch
        ]
        try:    
            results = self._client.models.embed_content(
                model=self._config.model,
                contents=contents,
                config={
                    "output_dimensionality": self._config.embedding_size
                }
            )

            actual_dimensionality = len(results.embeddings[0].values)
            if actual_dimensionality != self._config.embedding_size:
                raise EmbeddingFailed(
                    F"API returned unexpected dimensionality {actual_dimensionality} for model {self._config.model}, expected {self._config.embedding_size}",
                    permanent=True
                )
            # TODO: check if the embeddings are empty
            return [embedding.values for embedding in results.embeddings]

        except errors.ClientError as e:
            # ClientError: If the status code is in the 4xx range.
            # 429 (rate limit and quota exceeded)
            if e.code == 429:
                raise EmbeddingFailed(f"Rate limited: {e}", permanent=False)
            raise EmbeddingFailed(f"Client error: {e}", permanent=True)

        except errors.ServerError as e:
            # ServerError: If the status code is in the 5xx range.
            # 503 (DEADLINE_EXCEEDED), could be due to the prompt is too long or the server is overloaded,
            # better to retry, any way the policy retry governs by limiting the number of retries
            if e.code == 503:
                raise EmbeddingFailed(f"Service unavailable: {e}", permanent=False)
            raise EmbeddingFailed(f"Server error: {e}", permanent=True)

        except errors.APIError as e:
            # for other errors
            raise EmbeddingFailed(f"API error: {e}", permanent=True)    

    def _apply_task(self, text: str) -> str:
        return f"title: none | text: {text}"