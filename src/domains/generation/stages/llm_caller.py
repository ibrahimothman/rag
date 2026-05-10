"""
LLMCaller — interface for calling a language model with a Prompt
and streaming back text fragments.

This interface is the ACL boundary between Generation's domain and
the LLM vendor. Implementations handle all vendor-specific concerns:
message format, streaming protocol, error codes, model names.

The interface speaks domain language (Prompt in, str fragments out).
Vendor types never cross this boundary into the domain.
"""

from abc import ABC, abstractmethod
from typing import Iterator

from src.domains.generation.domain import (
    Prompt,
    SystemInstructions,
    GroundingChunk
)
from src.domains.generation.stages.llm_generation_model import LLMGenerationModel




class LLMCaller:

    def __init__(self, model: LLMGenerationModel) -> None:
        self._model = model


    @property
    def model_name(self) -> str:
        return self._model.model_name
    
    def call(self, prompt: Prompt) -> Iterator[str]:
        """
        Domain-facing operation.

        Takes a structured domain Prompt, serializes it into a model prompt,
        then streams text fragments from the underlying LLM generation model.

        Raises:
            StreamingFailed
        """

        system_instructions = self._build_system_instruction(prompt.instructions)
        user_content = self._build_user_content(prompt.question, prompt.grounding)


        for chunk in self._model.stream(system_instructions, user_content):
            yield chunk


    def _build_system_instruction(self, instructions: SystemInstructions) -> str:
        return "\n\n".join([
            instructions.role,
            instructions.grounding_rule,
            instructions.citation_rule,
            instructions.refusal_rule,
        ])
    
    def _build_user_content(self, question: str, grounding: tuple[GroundingChunk, ...]) -> str:
        grounding_text = "\n\n".join(
            f"[chunk-{index}] {chunk.content}"
            for index, chunk in enumerate(grounding, start=1)
        )

        return f"""
            Context:
            {grounding_text if grounding_text else "No grounding context was provided."}

            Question:
            {question}
            """.strip()
    

    
        

