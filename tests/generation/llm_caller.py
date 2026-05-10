import pytest
from unittest.mock import MagicMock

from uuid import uuid4

from src.domains.generation.stages import (
    LLMCaller, _DEFAULT_SYSTEM_INSTRUCTIONS, StreamingFailed
)
from src.domains.generation.domain import (
    Citation,
    GroundingChunk,
    Prompt
)

from src.domains.generation.infrastructure import (
    GeminiGeneration, GeminiGenerationConfig
)

from google.genai import errors


@pytest.fixture
def generation_model():
    return GeminiGeneration(GeminiGenerationConfig(
        model="gemini-pro", api_key="test" ))

def test_format_contents_includes_chunk_labels(generation_model):
    caller = LLMCaller(generation_model)

    grounding_chunk = GroundingChunk(
        chunk_id=uuid4(),
        content="Serializable isolation prevents phantom reads.",
        citation=Citation(document_id=uuid4()),
    )
    prompt = Prompt(
        instructions=_DEFAULT_SYSTEM_INSTRUCTIONS,
        question="How does isolation work?",
        grounding=(grounding_chunk,),
    )
    contents = caller._build_user_content(prompt.question, prompt.grounding)
    
    print (contents)
    assert "[chunk-1]" in contents
    assert "Serializable isolation" in contents
    assert "How does isolation work?" in contents



def test_rate_limit_raises_transient_failure(generation_model):
    error = errors.ClientError(code=429, response_json={"message": "Rate limit exceeded"})
    generation_model._client.models.generate_content = MagicMock(
        side_effect=error
    )
    
    system_instructions = _DEFAULT_SYSTEM_INSTRUCTIONS
    user_content = "What is the capital of France?"

    with pytest.raises(StreamingFailed) as e:
        list(generation_model.stream(system_instructions, user_content))

    assert e.value.permanent is False 


