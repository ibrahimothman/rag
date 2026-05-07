from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class SourceFile:
    location: str
    mime_type: str


@dataclass(frozen=True)
class ExtractedDocument:
    id: UUID
    text: str
    page_count: int | None = None
    metadata: dict | None = None


class Extractor(ABC):
    """Extract text from a source file"""

    
    @abstractmethod
    def supports(self, mime_type: str) -> bool:
        """Check if the extractor can handle the given mime type"""
    
    @abstractmethod
    def extract(self, source_file: SourceFile) -> ExtractedDocument:
        """Extract text. Raises ExtractionFailed on permanent failures."""


class ExtractionFailed(Exception):
    def __init__(self, message: str, permanent: bool):
        self.message = message
        self.permanent = permanent