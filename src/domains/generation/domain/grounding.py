
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class Citation: 
    """
    Provenance pointing back to the source document.
    
    Mirrors Retrieval's Citation — same data, Generation's own type.
    Identity is preserved via document_id.
    """
    
    document_id: UUID
    page_number: int | None = None

@dataclass(frozen=True)
class GroundingChunk:
    """
    A chunk serving as grounding material for answer generation.
    
    Generation's own representation of what Retrieval found.
    Does not carry a similarity score — that was Retrieval's concern.
    Carries chunk_id so resolved citations can be traced back to
    the original chunk in Ingestion's store.
    """

    chunk_id: UUID
    content: str
    citation: Citation