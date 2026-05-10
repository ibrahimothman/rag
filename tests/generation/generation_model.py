import os
import pytest
from dotenv import load_dotenv
from uuid import uuid4

from src.domains.generation.stages import StreamingFailed, LLMCaller
from src.domains.generation.infrastructure import (
    GeminiGenerationConfig,
    GeminiGeneration,
)
from src.domains.generation.domain import (
    Citation,
    GroundingChunk,
    Prompt
)


import pytest

from src.domains.generation.stages import LLMCaller, construct_prompt


load_dotenv()

@pytest.fixture
def llm_caller():
    api_key = os.getenv("GEMINI_API_KEY")

    if api_key is None:
        pytest.skip("GEMINI_API_KEY is not set")

    assert api_key is not None    

    model = GeminiGeneration(
        GeminiGenerationConfig(
            model="gemini-3-flash-preview",
            api_key=api_key,
        )
    )
    return LLMCaller(model)    


def _make_grounding(*texts: str):
    
    return tuple(
        GroundingChunk(
            chunk_id=uuid4(),
            content=text,
            citation=Citation(document_id=uuid4()),
        )
        for text in texts
    )

# def test_gemini_generation_model_streams_real_text(llm_caller):
    

#     grounding = _make_grounding(
#         "Serializable isolation is the strongest isolation level in databases. "
#         "It ensures transactions appear to execute sequentially.",
#         "Phantom reads occur when a transaction reads a set of rows, "
#         "another transaction inserts a row, and the first transaction "
#         "re-reads and sees the new row.",
#     )

#     prompt = construct_prompt(
#         question="What is serializable isolation?",
#         grounding=grounding
#     )

#     fragments = list(llm_caller.call(prompt))

    
#     assert len(fragments) > 0, (
#         f"Expected multiple fragments from streaming generation, got {len(fragments)}."
#         "Streaming may not be working as intended."
#     )

#     # each fragment should be a non-empty string
#     for i, fragment in enumerate(fragments):
#         assert isinstance(fragment, str), f"Fragment {i} is not a string."
#         assert len(fragment) > 0, f"Fragment {i} is empty."


def test_empty_grounding_produces_honest_answer(llm_caller):
        """
        With no grounding, the LLM should produce an answer but it
        should contain no citation markers (nothing to cite).
        
        Verifies the pipeline handles the EMPTY_INPUT case gracefully.
        """
        prompt = construct_prompt(
            question="What is the capital of France?",
            grounding=(),    # no grounding
        )

        fragments = list(llm_caller.call(prompt))
        full_answer = "".join(fragments)

        # Should still produce an answer (general knowledge)
        assert len(full_answer) > 0

        # Should not contain citation markers (nothing to cite)
        assert "[chunk-" not in full_answer, (
            "Expected no citation markers with empty grounding "
            f"but got: {full_answer[:200]}"
        )        

    