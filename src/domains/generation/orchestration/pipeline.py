"""
GenerationPipeline — orchestrates the prompt construction, LLM call,
streaming, and citation resolution for a single generation request.

The pipeline emits events as it runs:
- GenerationStarted: immediately on entry
- AnswerChunk × N: one per text fragment from the LLM stream
- GenerationCompleted: after citation resolution, with full answer
- GenerationFailed: if any stage fails, with optional partial answer
"""

from uuid import UUID, uuid4
import time

from src.domains.generation.domain import (
    GroundingChunk,
    GenerationFailureReason,
    GenerationFailureKind,
    GroundingQuality,
    Prompt
)
from src.domains.generation.stages import (
    LLMCaller,
    StreamingFailed,
    resolve_citations,
    construct_prompt
)

from src.domains.generation.api import (
    GenerationStarted,
    GenerationCompleted,
    GenerationFailed,
    AnswerChunk,

)

from src.domains.generation.orchestration.event_publisher import EventPublisher




class GenerationPipeline:
    def __init__(
        self, 
        llm_caller: LLMCaller,
        events: EventPublisher,
    ):
        self._llm_caller = llm_caller
        self._events = events

    def run(
        self, 
        request_id: UUID, 
        question: str, 
        grounding: tuple[GroundingChunk, ...]
    ) -> None:
        
        started_at = time.monotonic()
        generation_id = uuid4()

        self._events.publish(GenerationStarted(
            request_id=request_id,
            generation_id=generation_id,
            question=question,
        ))
        
        prompt = construct_prompt(question, grounding)

        try:
            full_answer = self._stream_answer(
                request_id=request_id,
                generation_id=generation_id,
                prompt=prompt
            )

        except _StageFailure as f:

            self._events.publish(GenerationFailed(
                request_id=request_id,
                generation_id=generation_id,
                reason=f.reason,
                partial_answer=f.partial_answer,
                duration_ms=int((time.monotonic() - started_at) * 1000)
            ))

            return
            

        citation_map = resolve_citations(full_answer, grounding)

        grounding_quality = GroundingQuality.assess(
            citation_map=citation_map, 
            grounding_count=len(grounding)
        )

        self._events.publish(GenerationCompleted(
            request_id=request_id,
            generation_id=generation_id,
            question=question,
            full_answer=full_answer,
            citations=citation_map.entries,
            grounding_quality=grounding_quality.value,
            unresolved_markers=citation_map.unresolved_markers,
            duration_ms=int((time.monotonic() - started_at) * 1000)
        ))

        return
    


    def _stream_answer(
        self, 
        request_id: UUID,
        generation_id: UUID,
        prompt: Prompt
    ) -> str:
        """
        Call the LLM, stream fragments back as AnswerChunk events,
        and return the assembled full answer.

        Raises _StageFailure on LLM errors, carrying any partial
        answer assembled before the failure.
        """
        fragments = [] 
        try:
            stream = self._llm_caller.call(prompt)
            for sequence, fragment in enumerate(stream, start=1):
                fragments.append(fragment)
                self._events.publish(AnswerChunk(
                    request_id=request_id,
                    generation_id=generation_id,
                    text=fragment,
                    sequence=sequence
                ))


        except StreamingFailed as f:
            raise _StageFailure(GenerationFailureReason(
                stage="LLM_CALL",
                kind=GenerationFailureKind.PERMANENT if f.permanent else GenerationFailureKind.TRANSIENT,
                message=f.message
            ), partial_answer="".join(fragments) if fragments else None)

        return "".join(fragments)
       


          

class _StageFailure(Exception):
    """Raised when a stage in the pipeline fails."""
    def __init__(self, reason: GenerationFailureReason, partial_answer: str | None = None):
        super().__init__(reason.message)
        self.reason = reason
        self.partial_answer = partial_answer

    