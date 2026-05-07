from dataclasses import dataclass

@dataclass(frozen=True)
class Query:
    """
    The text query as received from the caller.
    
    Frozen because queries don't mutate — once received, the text is fixed.
    Anything Retrieval does to "transform" the query produces a new value
    (an EmbeddedQuery), not a mutation of this one.
    """
    text: str


@dataclass(frozen=True)
class EmbeddedQuery:
    """
    A query enriched with its vector embedding, ready for similarity search.
    
    Carries the original query for traceability and the embedding for the
    actual search operation. Carries the embedding model version because
    the vector is only valid relative to a specific model.
    """
    query: Query
    vector: list[float]
    embedding_model_version: str
    