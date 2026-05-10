
from dataclasses import dataclass, field
from uuid import UUID
from src.domains.generation.domain import CitationEntry, GenerationFailureReason



@dataclass(frozen=True)
class GenerationStarted:
    request_id: UUID
    generation_id: UUID
    question: str


# This event is emitted each time a new chunk is added to the answer stream during generation.
@dataclass(frozen=True)
class AnswerChunk:
    request_id: UUID
    generation_id: UUID
    text: str
    sequence: int # chunks may arrive out of order.



@dataclass(frozen=True)
class GenerationCompleted:
    request_id: UUID
    question: str
    generation_id: UUID 
    full_answer: str
    citations: tuple[CitationEntry, ...]
    grounding_quality: str # "grounded" | "weak" | "ungrounded" | "empty_input"
    unresolved_markers: tuple[str, ...]  = field(default_factory=tuple)
    duration_ms: int = 0
    


@dataclass(frozen=True)
class GenerationFailed:
    request_id: UUID
    generation_id: UUID
    reason: GenerationFailureReason  
    partial_answer: str | None = None # non-None if steam was interrupted mid-way
    duration_ms: int = 0