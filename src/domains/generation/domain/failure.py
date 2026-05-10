from enum import Enum
from dataclasses import dataclass

class GenerationFailureKind(Enum):
    TRANSIENT = "transient" # retry may succeed (rate limit, network error, etc.)
    PERMANENT = "permanent" # retry won't help. (corrupt file, unsupported format, etc.)

@dataclass(frozen=True)
class GenerationFailureReason:
    kind: GenerationFailureKind
    message: str
    stage: str

    @property
    def is_retryable(self) -> bool:
        return self.kind == GenerationFailureKind.TRANSIENT

