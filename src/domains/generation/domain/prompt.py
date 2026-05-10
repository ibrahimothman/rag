
from dataclasses import dataclass
from src.domains.generation.domain.grounding import GroundingChunk


@dataclass(frozen=True)
class SystemInstructions:
    """
    The rules and role the LLM should follow when generating an answer.
    
    Includes:
    - The LLM's role definition ("You are a helpful assistant...")
    - Grounding rules ("Answer only based on provided context")
    - Citation rules ("Cite chunks using [chunk-N] notation")
    - Refusal rules ("If grounding is insufficient, say so honestly")
    - Formatting preferences
    """
    role: str
    grounding_rule: str
    citation_rule: str
    refusal_rule: str
    

@dataclass(frozen=True)
class Prompt:
    """
    The complete, structured input for the LLM.
    
    Composed of system instructions, the user's question, and the
    grounding chunks. The ACL serializes this into whatever format
    the target LLM expects.
    
    Keeping this as a structured domain object (rather than a string)
    means prompt construction logic lives in the domain, not scattered
    across infrastructure. It also makes prompts testable without
    calling a real LLM.
    """
    instructions: SystemInstructions
    question: str
    grounding: tuple[GroundingChunk, ...]
    
    @property
    def has_grounding(self) -> bool:
        """True if there is any grounding material to base an answer on."""
        return len(self.grounding) > 0
    
    @property
    def grounding_count(self) -> int:
        """Number of grounding chunks available."""
        return len(self.grounding)