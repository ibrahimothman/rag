"""
Smoke test: ingest one document end-to-end.
Usage: python scripts/ingest_one.py /path/to/file.pdf
"""

from src.domains.ingestion.config import load_ingestion_config_from_env
from src.domains.ingestion.composition import build_ingestion
from src.domains.ingestion.observability.logging_subscriber import log_event
from src.domains.ingestion.api.commands import IngestDocument
import uuid
import sys
from pathlib import Path
import logging
from dotenv import load_dotenv

def main(file_path: str, mime_type: str):
    load_dotenv()
    logging.basicConfig(level=logging.INFO)

    config = load_ingestion_config_from_env()
    handler = build_ingestion(config, [log_event])

    # simulate an incoming command
    command = IngestDocument(
        document_id=uuid.uuid4(),
        source_location=file_path,
        mime_type=mime_type,
    )
    try:
        handler.handle_ingest(command)
    except Exception as e:
        print(f"x Ingestion crashed: {type(e).__name__}: {e}")
        raise

if __name__ == "__main__":
    uploads_dir = Path("assets/files")
    file = uploads_dir / "ddd.pdf"
    mime_type = "application/pdf" if file.suffix.lower() == ".pdf" else "text/plain"
    main(str(file), mime_type)
   