from dataclasses import dataclass

from src.domains.generation.domain.grounding import Citation
    
@dataclass(frozen=True)
class CitationEntry:
    """
    A single resolved citation: a marker in the answer text
    mapped to its source.
    
    The marker is the string the LLM used in the answer text
    (e.g., "chunk-3" for the text "[chunk-3]"). The chunk_id
    and citation trace it back to the source document.
    """

    marker: str
    chunk_id: str
    citation: Citation

@dataclass(frozen=True)
class CitationMap:
    """
    The complete resolution of all citation markers in one answer.
    
    Built after streaming completes by scanning the assembled answer
    for [chunk-N] markers and resolving each against the grounding
    chunks provided in the Prompt.
    
    Unresolved markers (LLM cited a chunk not in the grounding) are
    tracked separately so callers can assess hallucination risk.
    """
    entries: tuple[CitationEntry, ...]
    unresolved_markers: tuple[str, ...]


    @property
    def is_empty(self) -> bool:
        """
        True if the answer did not cite any chunks.
        """
        return len(self.entries) == 0

    @property
    def has_hallucinated_citations(self) -> bool:
        """
        True if the answer cited chunks that were not in the grounding.
        A signal of potential hallucination.
        """
        return len(self.unresolved_markers) > 0
    
