from dataclasses import dataclass
from uuid import UUID

from src.domains.conversation.domain import UserMessage




@dataclass(frozen=True)
class Citation:
    """
    Provenance information pointing back to the source document.
    """
    document_id: UUID
    page: int | None = None

@dataclass(frozen=True)
class GroundingEntry:
    """
    A chunk serving as grounding material for answer generation.
    """
    chunk_id: UUID
    content: str
    citation: Citation

@dataclass(frozen=True)
class GroundingResult:
    """
    A list of grounding results.
    """
    conversation_id: UUID
    retrieval_id: UUID
    message: UserMessage
    results: tuple[GroundingEntry, ...] = ()

  