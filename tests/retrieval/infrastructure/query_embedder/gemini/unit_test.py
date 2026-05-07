import pytest
from unittest.mock import patch, MagicMock

from src.domains.retrieval.infrastructure.query_embedder.gemini import (
    GeminiQueryEmbedder, 
    GeminiQueryEmbedderConfig, 
    QueryEmbeddingFailed
)
from src.domains.retrieval.domain.query import Query
from google.genai import errors

@pytest.fixture()
def config():
    return GeminiQueryEmbedderConfig(
        model="gemini-embedding-2",
        embedding_size=1536,
        api_key="fake_api_key"
    )
@pytest.fixture
def embedder(config):
    with patch("src.domains.retrieval.infrastructure.query_embedder.gemini.genai.Client"):
        return GeminiQueryEmbedder(config)

def _mock_response(vector: list[float]):
    embedding = MagicMock()
    embedding.values = vector
    
    response = MagicMock()
    response.embeddings = [embedding]
    return response
        
def test_successful_embedding_returns_embedded_query(embedder):
    fake_vector = [0.1, 0.2]
    embedder._client.models.embed_content = MagicMock(
        return_value=_mock_response(fake_vector)
    )

    query = Query(text="What is the capital of France?")
    result = embedder.embed(query)
    assert result.query == query
    assert result.vector == fake_vector
    assert result.embedding_model_version == "gemini-embedding-2@1536"


def test_rate_limit_raises_transient_failure(embedder):
    error = errors.ClientError(code=429, response_json={"message": "Rate limit exceeded"})
    embedder._client.models.embed_content = MagicMock(
        side_effect=error
    )
    query = Query(text="What is the capital of France?")
    with pytest.raises(QueryEmbeddingFailed) as e:
        embedder.embed(query)

    assert e.value.permanent is False    

def test_empty_embedding_raises_permanent_failure(embedder):
    embedder._client.models.embed_content = MagicMock(
        return_value=_mock_response([])
    )
    query = Query(text="What is the capital of France?")
    with pytest.raises(QueryEmbeddingFailed) as e:
        embedder.embed(query)

    assert e.value.permanent is True    