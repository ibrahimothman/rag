
from abc import ABC

from src.domains.generation.domain import Prompt, GroundingChunk, SystemInstructions


_DEFAULT_SYSTEM_INSTRUCTIONS = SystemInstructions(
    role=(
        "You are a helpful assistant that answers questions using "
        "only the provided grounding material."
    ),
    grounding_rule=(
        "Use only the provided context chunks as the source of truth. "
        "Do not use external knowledge or make unsupported assumptions."
    ),
    citation_rule=(
        "When you use information from a chunk, cite it using the format "
        "[chunk-N], where N is the chunk number shown in the context."
    ),
    refusal_rule=(
        "If the provided context does not contain enough information to "
        "answer the question, say that the available documents do not "
        "provide enough information."
    ),
)


def construct_prompt(question: str, grounding: tuple[GroundingChunk, ...]) -> Prompt:
    """
    Build a structured Prompt for answer generation.

    This function creates the domain-level prompt object.
    It does not serialize the prompt into Gemini/OpenAI format.
    Vendor-specific serialization is handled by the LLM adapter.
    """
    
    return Prompt(
        instructions=_DEFAULT_SYSTEM_INSTRUCTIONS,
        question=question,
        grounding=grounding
    )


