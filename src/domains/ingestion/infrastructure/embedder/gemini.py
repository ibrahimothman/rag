
from src.domains.ingestion.stages.embedder import Embedder, EmbeddingFailed
from src.domains.ingestion.domain.chunk import Chunk, EmbeddedChunk
from src.shared.gemini import GeminiProviderClient, GeminiError

from dataclasses import dataclass

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
    batch_size: int = 100

class GeminiEmbedder(Embedder):
    
    """
    Embeds chunks using Google Gemini's embeddings API.
    
    Sends chunks in batches to limit API call count. Classifies failures:
    rate limits, timeouts, and connection errors are transient (retry-worthy);
    auth errors and malformed requests are permanent.
    """
    
    def __init__(self, config: GeminiEmbedderConfig, gemini: GeminiProviderClient):
        self._config = config
        self._gemini = gemini

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
            results = self._gemini.client.models.embed_content(
                model=self._config.model,
                contents=contents,
                config={
                    "output_dimensionality": self._config.embedding_size
                }
            )
        except GeminiError as e:
            gemini_error = self._gemini.translate_error(e)
            raise EmbeddingFailed(
                message=gemini_error.message,
                permanent=gemini_error.permanent
            )
        
        if not results or not results.embeddings or not results.embeddings[0] or not results.embeddings[0].values:
            raise EmbeddingFailed(
                "API returned empty embeddings",
                permanent=True
            )
        
        actual_dimensionality = len(results.embeddings[0].values)
        if actual_dimensionality != self._config.embedding_size:
            raise EmbeddingFailed(
                F"API returned unexpected dimensionality {actual_dimensionality} for model {self._config.model}, expected {self._config.embedding_size}",
                permanent=True
            )
        # TODO: check if the embeddings are empty
        return [embedding.values for embedding in results.embeddings]

    def _apply_task(self, text: str) -> str:
        return f"title: none | text: {text}"