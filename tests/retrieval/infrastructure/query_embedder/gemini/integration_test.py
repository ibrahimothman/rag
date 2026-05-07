import pytest
import dotenv
import os
from uuid import uuid4
import numpy as np

from src.domains.ingestion.infrastructure.embedder.gemini import (
    GeminiEmbedder, 
    GeminiEmbedderConfig
)
from src.domains.retrieval.infrastructure.query_embedder.gemini import (
    GeminiQueryEmbedder, 
    GeminiQueryEmbedderConfig
)

from src.domains.ingestion.domain.chunk import Chunk
from src.domains.retrieval.domain.query import Query


dotenv.load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

@pytest.mark.integration
@pytest.mark.skipif(
    GEMINI_API_KEY is None,
    reason="GEMINI_API_KEY not set; skipping live API test",
)
def test_query_and_docuemnt_embeddings_are_simlilar_for_related_text():
    document_embedder = GeminiEmbedder(GeminiEmbedderConfig(
        model="gemini-embedding-2",
        embedding_size=1536,
        api_key=GEMINI_API_KEY
    ))

    query_embedder = GeminiQueryEmbedder(GeminiQueryEmbedderConfig(
        model="gemini-embedding-2",
        embedding_size=1536,
        api_key=GEMINI_API_KEY
    ))

    document_text = (
        "Serializable isolation is the gold standard of database consistency,"
        "ensuring that the final state of your data is the same as if every transaction had waited its turn to run one at a time"
        "Even though the database might actually be running many tasks at once to keep things fast,"
        "it uses strict locking or conflict detection to prevent errors like phantom reads or write skew."
    )

    query_text = "How do databases prevent phantom reads?"

    # embed the document asa chunk
    chunk = Chunk(
        id=uuid4(),
        text=document_text,
        source_document_id=uuid4(),
        position=0,
        chunking_strategy_version="fixed_size_v1",
        metadata={}
    )

    embedded_chunks = document_embedder.embed([chunk])
    doc_vector = np.array(embedded_chunks[0].vector)

    # embed the query
    embedded_query = query_embedder.embed(Query(text=query_text))
    query_vector = np.array(embedded_query.vector)

    # cosine similarity between the query and the chunk
    cosine_similarity = float(
        np.dot(doc_vector, query_vector) / 
        (np.linalg.norm(doc_vector) * np.linalg.norm(query_vector))
    )

    assert cosine_similarity > 0.5, (
        f"Expected cosine similarity > 0.5, but got {cosine_similarity}"
    )