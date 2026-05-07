import pytest
from .gemini import GeminiEmbedder, GeminiEmbedderConfig
from ...domain.chunk import Chunk
from unittest.mock import MagicMock, patch
from uuid import uuid4
from types import SimpleNamespace
from google.genai import errors
from ...stages.embedder import EmbeddingFailed



def _create_chunk(text: str) -> Chunk:
    return Chunk(
        id=uuid4(), 
        text=text, 
        source_document_id=uuid4(), 
        position=0, 
        metadata={}
    )

def test_returns_empty_for_empty_input():
    embedder = GeminiEmbedder(GeminiEmbedderConfig(embedding_size=3072, api_key="fake_api_key"))
    assert embedder.embed([]) == []


def test_embeds_chunks_in_order():
    embedder = GeminiEmbedder(GeminiEmbedderConfig(embedding_size=2, api_key="fake_api_key"))

    fake_response = MagicMock()
    fake_response.embeddings = [
        SimpleNamespace(values=[0.1, 0.2]),
        SimpleNamespace(values=[0.4, 0.5])
    ]

    with patch.object(embedder._client.models, "embed_content", return_value=fake_response):
        chunks = [_create_chunk("chunk 1"), _create_chunk("chunk 2")]
        result = embedder.embed(chunks)
    
    assert len(result) == 2
    assert result[0].vector == [0.1, 0.2]
    assert result[1].vector == [0.4, 0.5]


def test_rate_limit_failure_is_transient():
    embedder = GeminiEmbedder(GeminiEmbedderConfig(embedding_size=2, api_key="fake_api_key"))

    with patch.object(
        embedder._client.models, "embed_content", 
        side_effect=errors.ClientError(code=429, response_json={"message": "Rate limit exceeded"}),
    ):

        with pytest.raises(EmbeddingFailed) as e:
            embedder.embed([_create_chunk("chunk 1")])

        assert e.value.permanent is False


def test_auth_error_is_permanent(): 
    embedder = GeminiEmbedder(GeminiEmbedderConfig(embedding_size=2, api_key="fake_api_key"))

    with patch.object(
        embedder._client.models, "embed_content", 
        side_effect=errors.ClientError(code=401, response_json={"message": "Invalid API key"}),
    ):

        with pytest.raises(EmbeddingFailed) as e:
            embedder.embed([_create_chunk("chunk 1")])

        assert e.value.permanent is True