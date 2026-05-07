from uuid import UUID
from dataclasses import dataclass

@dataclass(frozen=True)
class IngestDocument:
    """Begin ingesting a document into the searchable index"""
    document_id: UUID
    source_location: str
    mime_type: str


@dataclass(frozen=True)
class ReingestDocument:
    """Reprocess an ingested document (e.g., after model upgrade)"""
    document_id: UUID
    source_location: str
    mime_type: str


@dataclass(frozen=True)
class RetryIngestion:
    """Stop a running ingestion job"""
    job_id: UUID
    source_location: str
    mime_type: str

