from datetime import datetime, timezone

from ..stages.extractor import Extractor, SourceFile, ExtractionFailed
from ..stages.chunker import Chunker, ExtractedDocument
from ..stages.embedder import Embedder, EmbeddingFailed
from ..stages.chunk_index import ChunkIndex, IndexingFailed
from .job_repository import JobRepository
from .event_publisher import EventPublisher
from ..domain.job import IngestionJob
from ..domain.chunk import Chunk, EmbeddedChunk
from ..domain.stages import IngestionStage
from ..api.events import IngestionStarted, DocumentIndexed, IngestionFailed
from ..domain.failure import FailureReason, FailureKind

class Pipeline:

    def __init__(
        self,
        extractors: list[Extractor],
        chunker: Chunker,
        embedder: Embedder,
        chunk_index: ChunkIndex,
        jobs: JobRepository,
        events: EventPublisher,

    ):
        self._extractors = extractors
        self._chunker = chunker
        self._embedder = embedder
        self._chunk_index = chunk_index
        self._jobs = jobs
        self._events = events

    def run(self, job: IngestionJob, source_file: SourceFile) -> None:
        """Run the pipeline"""

        try:
            extracted_document = self._extract_and_advance(job, source_file)
            chunks = self._chunk_and_advance(job, extracted_document)
            embedded_chunks = self._embed_and_advance(job, chunks)
            self._index_and_complete(job, embedded_chunks)
        except _StageFailure as e:
            self._record_failure(job, e.failure_reason)
           


    # ------- Stage methods -------
       
    def _extract_and_advance(self, job: IngestionJob, source_file: SourceFile) -> None:

        job.advance_to(IngestionStage.EXTRACTING)
        self._jobs.save(job)
        self._events.publish(IngestionStarted(
            document_id=job.document_id,
            job_id=job.id,
            started_at=datetime.now(timezone.utc),
        ))

        try:
            
            return self._pick_extractor(source_file.mime_type).extract(source_file)
        except ExtractionFailed as e:
            raise _StageFailure(
                FailureReason(
                kind=FailureKind.PERMANENT if e.permanent else FailureKind.TRANSIENT,
                message=e.message,
                stage=IngestionStage.EXTRACTING)
            )


    def _chunk_and_advance(self, job: IngestionJob, extracted_document: ExtractedDocument) -> None:

        job.advance_to(IngestionStage.CHUNKING)
        self._jobs.save(job)
        return self._chunker.chunk(extracted_document)


    def _embed_and_advance(self, job: IngestionJob, chunks: list[Chunk]) -> None:

        job.advance_to(IngestionStage.EMBEDDING)
        self._jobs.save(job)

        try:
            return self._embedder.embed(chunks)
        except EmbeddingFailed as e:
            raise _StageFailure(FailureReason(
                kind=FailureKind.PERMANENT if e.permanent else FailureKind.TRANSIENT,
                message=e.message,
                stage=IngestionStage.EMBEDDING)
            )

    def _index_and_complete(self, job: IngestionJob, embedded_chunks: list[EmbeddedChunk]) -> None:
        
        job.advance_to(IngestionStage.INDEXING)
        self._jobs.save(job)
        try:
            self._chunk_index.write_for_document(job.document_id, embedded_chunks)
        except IndexingFailed as e:
            raise _StageFailure(FailureReason(
                kind=FailureKind.PERMANENT if e.permanent else FailureKind.TRANSIENT,
                message=e.message,
                stage=IngestionStage.INDEXING)
            )
        job.advance_to(IngestionStage.COMPLETED)
        self._jobs.save(job)
        self._events.publish(DocumentIndexed(
            document_id=job.document_id,
            job_id=job.id,
            chunk_count=len(embedded_chunks),
            indexed_at=datetime.now(timezone.utc),
        ))


    # ------- Failure recording -------
    
    def _record_failure(self, job: IngestionJob, failure_reason: FailureReason) -> None:
        job.mark_failed(failure_reason)
        self._jobs.save(job)
        self._events.publish(IngestionFailed(
            document_id=job.document_id,
            job_id=job.id,
            failure_reason=failure_reason,
            failed_at=datetime.now(timezone.utc),
        ))


    def _pick_extractor(self, mime_type: str) -> Extractor:
        for extractor in self._extractors:
            if extractor.supports(mime_type):
                return extractor
        raise ExtractionFailed(
            f"No extractor found for mime type: {mime_type}",
            permanent=True,
        )

class _StageFailure(Exception):
    def __init__(self, failure_reason: FailureReason):
        self.failure_reason = failure_reason
        
       




        