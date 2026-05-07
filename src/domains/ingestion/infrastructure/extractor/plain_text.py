from ...stages.extractor import Extractor, SourceFile, ExtractedDocument, ExtractionFailed
from pathlib import Path
from uuid import uuid4


class PlainTextExtractor(Extractor):
    """
    Extracts text from plain-text files.
    
    Reads the file at source.location, decodes it as UTF-8, and returns its
    content as an ExtractedDocument. Treats decoding errors as permanent
    failures (the file isn't really plain text).
    """

    _SUPPORTED_MIME_TYPES = frozenset({"text/plain", "text/markdown", "text/html"})

    _EXTRACTOR_VERSION = "plain_text_v1"

    def supports(self, mime_type: str) -> bool:
        return mime_type.lower() in self._SUPPORTED_MIME_TYPES
    
    
    def extract(self, source_file: SourceFile) -> ExtractedDocument:
        # TODO: source location could be a local path, S3 URI, a presigned URL, etc.
        # Option A: Each extractor handles all location types it cares about.
        # Option B: A SourceFetcher abstraction to read the file and pass the bytes regardless of where it lives.
        path = Path(source_file.location)
        if not path.exists():
            raise ExtractionFailed(
                f"Source file not found: {source_file.location}",
                permanent=True,
            )
        
        try:
            with path.open("r", encoding="utf-8") as file:
                text = file.read()
        except UnicodeDecodeError as e:
            raise ExtractionFailed(
                f"Failed to decode file as UTF-8: {e}",
                permanent=True,
            )

        except OSError as e:
            # IO errors are usually transient e.g. disk hiccups, permission issues, etc.
            raise ExtractionFailed(
                f"Failed to read file: {e}",
                permanent=False,
            )
        return ExtractedDocument(
            id=uuid4(),
            text=text,
            page_count=None,
            metadata={
                "source_location": source_file.location,
                "mime_type": source_file.mime_type,
                "size": path.stat().st_size,
                "extractor_version": self._EXTRACTOR_VERSION,
            },
        )