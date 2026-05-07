from dataclasses import dataclass
from uuid import UUID


#TODO: we need to add the page number to the publiched language (chubnks schema) between Retreival and Ingestion domains
@dataclass(frozen=True)
class Citation:
    """
    Provenance information pointing back to the source document.
    
    Includes the document identifier and any additional metadata
    (page number, section, etc.) needed to attribute the chunk's
    content to its origin.
    """
    document_id: UUID
    page: int | None = None

@dataclass(frozen=True)
class ScoredChunk:
    """
    A chunk paired with its similarity score for a given query.
    
    Score is similarity in [-1, 1] where 1.0 is a perfect match.
    Computed as 1 - cosine_distance for normalized embeddings.
    
    Includes a Citation so the caller can attribute the chunk's content
    to its source document.
    """
    chunk_id: UUID
    content: str
    score: float
    citation: Citation
