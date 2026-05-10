

from abc import ABC, abstractmethod
from typing import Iterator


class LLMGenerationModel(ABC):


    @property
    @abstractmethod
    def model_name(self) -> str:
        """The name of the LLM model being called (e.g. "gpt-4")."""
        ...
    @abstractmethod
    def stream(self, systemInstructions: str, userContent: str) -> Iterator[str]:
        """
        Call the LLM with a serialized prompt and stream text fragments.

        Raises:
            StreamingFailed
        """
        ... 

class StreamingFailed(Exception):
    """Raised when the LLM call fails (e.g. network error, API error)."""
    def __init__(self, message: str, permanent: bool = False):
        super().__init__(message)
        self.message = message
        self.permanent = permanent        