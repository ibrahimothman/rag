"""
Smoke test: retrieve relevant chunks from the vector database.
"""

from src.domains.retrieval.config import load_retrieval_config_from_env
from src.domains.retrieval.composition import build_retrieval
from src.domains.retrieval.observability.logging_subscriber import log_event
from src.domains.retrieval.api.commands import RetrieveRelevantChunks
import uuid
import sys
from pathlib import Path
import logging
from dotenv import load_dotenv

def main():
    load_dotenv()
    logging.basicConfig(level=logging.INFO)

    config = load_retrieval_config_from_env()
    handler = build_retrieval(config, [log_event])

    # simulate an incoming command
    command = RetrieveRelevantChunks(
        request_id=uuid.uuid4(),
        query_text="What does PACELC stand for?"
    )
    try:
        handler.handle_retrieve(command)
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        raise

if __name__ == "__main__":
    main()
   