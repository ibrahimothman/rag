from ...stages.extractor import Extractor, SourceFile, ExtractedDocument, ExtractionFailed
from pathlib import Path
from uuid import uuid4
import pymupdf

class PdfExtractor(Extractor):
    """
    Extracts text from PDF files using pypdf.
    
    Reads each page's text and joins them with page separators. Encrypted PDFs
    that can't be decrypted, and structurally corrupt PDFs, are permanent
    failures. IO errors are transient.
    """

    _SUPPORTED_MIME_TYPES = frozenset({"application/pdf"})
    _EXTRACTOR_VERSION = "pdf_v1"
    _PAGE_SEPARATOR = "\n\n"

    def supports(self, mime_type: str) -> bool:
        return mime_type.lower() in self._SUPPORTED_MIME_TYPES

    def extract(self, source_file: SourceFile) -> ExtractedDocument:
        # TODO: scanned PDFs are not supported yet
        # very large PDFs
        path = Path(source_file.location)

        if not path.exists():
            raise ExtractionFailed(
                f"Source file not found: {source_file.location}",
                permanent=True,
            )

        try:
            doc = pymupdf.open(str(path))
        except pymupdf.FileDataError as e:
            # Corrupt or non-PDF file
            raise ExtractionFailed(
                f"Invalid or corrupt PDF: {e}",
                permanent=True,
            )
        except OSError as e:
            raise ExtractionFailed(
                f"Failed to read file: {e}",
                permanent=False,
            )
        
        try:
            if doc.is_encrypted:
                # Try empty password first
                if not doc.authenticate(""):
                    raise ExtractionFailed(
                        "PDF is password-protected",
                        permanent=True,
                    )
            
            page_texts: list[str] = []
            for page in doc:
                # "text" mode is plain reading-order text; other modes available
                page_texts.append(page.get_text("text"))
            
            page_count = doc.page_count
            full_text = self._PAGE_SEPARATOR.join(page_texts).strip()

            return ExtractedDocument(
                id=uuid4(),
                text=full_text,
                page_count=page_count,
                metadata={
                    "source_location": source_file.location,
                    "mime_type": source_file.mime_type,
                    "size": path.stat().st_size,
                    "extractor_version": self._EXTRACTOR_VERSION,
                    "pdf_metadata": dict(doc.metadata) if doc.metadata else {},
                },
            )

        finally:
            doc.close()