from src.domains.ingestion.stages.embedder import Embedder, EmbeddingFailed

class FlakyEmbedder(Embedder):
    """
    Wraps a real embedder; fails N times with transient errors before
    delegating to the wrapped one. Used to test retry logic.
    """
    def __init__(self, wrapped: Embedder, fail_count: int):
        self._wrapped = wrapped
        self._failure_remaining = fail_count

    @property
    def model_version(self) -> str:
        return self._wrapped.model_version
    
    def embed(self, chunks):
        if self._failure_remaining > 0:
            self._failure_remaining -= 1
            raise EmbeddingFailed(f"Failed to embed chunks", permanent=False)
        return self._wrapped.embed(chunks)

