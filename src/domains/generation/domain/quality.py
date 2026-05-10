
from enum import Enum

class GroundingQuality(Enum):
    """
    Assessment of how well the generated answer is grounded in
    the provided source material.
    
    GROUNDED    — answer cites chunks from the grounding; high confidence
    WEAK        — answer cites some chunks but sparsely; moderate confidence
    UNGROUNDED  — answer contains no citations; low confidence
    EMPTY_INPUT — no grounding was provided; answer is general knowledge only
    """

    GROUNDED = "grounded"
    WEAK = "weak"
    UNGROUNDED = "ungrounded"
    EMPTY_INPUT = "empty_input"

    @classmethod
    def assess(cls, citation_map: "CitationMap", grounding_count: int) -> "GroundingQuality":
        """
        Derive quality from the citation map and available grounding.
        
        Rules (V1 heuristics — refine based on measurement):
        - No grounding available at all → EMPTY_INPUT
        - No citations in answer → UNGROUNDED
        - Citations cover < 30% of available chunks → WEAK
        - Citations present and reasonable coverage → GROUNDED
        """
        from src.domains.generation.domain import CitationMap
        
        if grounding_count == 0:
            return cls.EMPTY_INPUT
        
        if citation_map.is_empty:
            return cls.UNGROUNDED
        
        # Coverage heuristic: what fraction of provided chunks were cited?
        cited_count = len(citation_map.entries)
        coverage = cited_count / grounding_count
        
        if coverage < 0.3:
            return cls.WEAK
        
        return cls.GROUNDED