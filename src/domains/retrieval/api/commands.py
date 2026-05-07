from dataclasses import dataclass
from uuid import UUID

@dataclass(frozen=True)
class RetrieveRelevantChunks:
    """
    The command to retrieve chunks from the vector database.
    """
    request_id: UUID
    query_text: str