from dataclasses import dataclass
from typing import Iterator

from src.domains.generation.stages import LLMGenerationModel, StreamingFailed

from google.genai import types


from src.shared.gemini import GeminiProviderClient, GeminiError


# TODO: strucutred output
@dataclass(frozen=True)
class GeminiGenerationConfig:
    model: str


class GeminiGeneration(LLMGenerationModel):
    def __init__(self, config: GeminiGenerationConfig, gemini: GeminiProviderClient):
        self._config = config
        self._gemini = gemini
        

    @property
    def model_name(self) -> str:
        return f"Gemini@{self._config.model}"

    def stream(self, system_instructions: str, user_content: str) -> Iterator[str]:
        try:
            response = self._gemini.client.models.generate_content_stream(
                model=self._config.model,
                contents=self._format_user_content(user_content),
                config=types.GenerateContentConfig(
                    system_instruction=system_instructions,
                ),
            )

            emitted_any_text = False

            for chunk in response:

                text = getattr(chunk, "text", None)
                if not text:
                    continue

                emitted_any_text = True
                
                yield text
        
        except GeminiError as e:
            gemini_error = self._gemini.translate_error(e)
            raise StreamingFailed(f"Gemini error: {gemini_error}", permanent=gemini_error.permanent)

        if not emitted_any_text:
                raise StreamingFailed("LLM did not emit any content", permanent=True)  
        
    def _format_user_content(self, user_content: str) -> list[dict]:
        return [
            {
                "role": "user",
                "parts": [{
                    "text": user_content
                }]
            }
        ]
        

    


