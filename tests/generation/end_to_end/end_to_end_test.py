
"""
End-to-end smoke test for the Generation context.

Runs a full generation cycle:
  1. Constructs the Generation stack via build_generation()
  2. Sends a GenerateAnswer command with hardcoded grounding
  3. Prints each AnswerChunk as it streams
  4. Prints the final answer, citations, and grounding quality

Usage:
    python -m tests.generation.end_to_end.end_to_end_test

Environment variables required:
    GEMINI_API_KEY — Google Gemini API key

No database needed — Generation is stateless.
"""

import logging
import os
import sys
from uuid import uuid4

from dotenv import load_dotenv

from src.domains.generation.composition import GenerationConfig, build_generation
from src.domains.generation.api import GenerateAnswer

from src.domains.generation.domain import GroundingChunk, Citation

from src.shared import log_event


load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("generate_one")


# ─── Hardcoded grounding for the smoke test ─────────────────────────────────
#
# In production, this would come from Retrieval's RetrievalResult.
# Here we simulate what Conversation would pass to Generation.

_GROUNDING = (
    GroundingChunk(
        chunk_id=uuid4(),
        content=(
            "Serializable isolation is the strongest isolation level in "
            "databases. It ensures that the outcome of concurrent "
            "transactions is the same as if they had executed sequentially, "
            "one at a time."
        ),
        citation=Citation(document_id=uuid4(), page_number=1),
    ),
    GroundingChunk(
        chunk_id=uuid4(),
        content=(
            "Phantom reads occur when a transaction reads a set of rows "
            "matching a condition, another transaction inserts a matching "
            "row, and the first transaction re-reads and sees the new row. "
            "Serializable isolation prevents this by locking the range."
        ),
        citation=Citation(document_id=uuid4(), page_number=2),
    ),
    GroundingChunk(
        chunk_id=uuid4(),
        content=(
            "Write skew is a subtle anomaly where two transactions read "
            "overlapping data and each writes to a different part, "
            "violating a constraint that neither write alone would violate. "
            "Serializable isolation prevents write skew via conflict detection."
        ),
        citation=Citation(document_id=uuid4(), page_number=3),
    ),
)

_QUESTION = (
    "How does serializable isolation work and what anomalies does it prevent?"
)



# ─── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY not set. Add it to .env or export it.")
        sys.exit(1)

    logger.info("Building Generation stack...")

    handler = build_generation(
        config=GenerationConfig(
            gemini_api_key=api_key,
            model="gemini-3-flash-preview",
        ),
        event_subscribers=[log_event],
    )

    command = GenerateAnswer(
        request_id=uuid4(),
        question=_QUESTION,
        grounding=_GROUNDING,
    )

    logger.info("Running generation...")

    try:
        handler.handle_generate(command)
        logger.info("Done.")
    except Exception as e:
        logger.exception(f"Generation crashed unexpectedly: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()