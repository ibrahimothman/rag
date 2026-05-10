
from dataclasses import dataclass, field
from uuid import UUID

from src.domains.generation.domain import GroundingChunk




@dataclass(frozen=True)
class GenerateAnswer:
    """
    Request Generation to produce a grounded answer.
    
    Carries:
    - request_id: caller's correlation ID (e.g., from Conversation)
    - question: the user's question to answer
    - grounding: chunks from Retrieval that should ground the answer
    """
    request_id: UUID
    question: str
    grounding: tuple[GroundingChunk, ...] = field(default_factory=tuple)