

from src.domains.generation.domain import GroundingChunk, CitationMap, CitationEntry

import re


_CHUNK_MARKER_PATTERN = re.compile(r"\[chunk-(\d+)\]")


def resolve_citations(
    answer: str,
    grounding: tuple[GroundingChunk, ...],
) -> CitationMap:
    """
    Resolve [chunk-N] markers in the answer against the grounding chunks.

    Example:
        answer contains: "[chunk-2]"
        grounding[1] is used because chunk numbers are 1-based.

    Returns:
        CitationMap containing resolved citation entries and unresolved markers.
    """

    # we use lists for the final output since they preserve order.
    # while sets are used to track seen markers and avoid duplicates.
    
    entries: list[CitationEntry] = []
    unresolved_markers: list[str] = []

    seen_resolved: set[str] = set()
    seen_unresolved: set[str] = set()

    for match in _CHUNK_MARKER_PATTERN.finditer(answer):
        marker_number = int(match.group(1))
        marker = f"chunk-{marker_number}"

        # LLM markers are 1-based: [chunk-1] means grounding[0]
        grounding_index = marker_number - 1

        if 0 <= grounding_index < len(grounding):
            chunk = grounding[grounding_index]

            # Avoid duplicate entries if the answer cites [chunk-1] multiple times
            if marker not in seen_resolved:
                entries.append(
                    CitationEntry(
                        marker=marker,
                        chunk_id=chunk.chunk_id,
                        citation=chunk.citation,
                    )
                )
                seen_resolved.add(marker)

        else:
            if marker not in seen_unresolved:
                unresolved_markers.append(marker)
                seen_unresolved.add(marker)

    return CitationMap(
        entries=tuple(entries),
        unresolved_markers=tuple(unresolved_markers),
    )