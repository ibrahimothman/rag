from enum import Enum
from dataclasses import dataclass
from .stages import IngestionStage

# TODO: the faulure can be more structured, with more details about the failure
# Categories (rate limit, timeout, authm quota exceeded, etc.)
# so a monitorting could track failures categories
# some metadata

class FailureKind(Enum):
    TRANSIENT = "transient" # retry may succeed (rate limit, network error, etc.)
    PERMANENT = "permanent" # retry won't help. (corrupt file, unsupported format, etc.)

@dataclass(frozen=True)
class FailureReason:
    kind: FailureKind
    message: str
    stage: IngestionStage

    @property
    def is_retryable(self) -> bool:
        return self.kind == FailureKind.TRANSIENT

@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int
    backoff_seconds: int

    @classmethod
    def default(cls) -> "RetryPolicy":
        return RetryPolicy(max_attempts=3, backoff_seconds=5)

