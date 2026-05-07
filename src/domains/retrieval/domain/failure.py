from dataclasses import dataclass
from enum import Enum

@dataclass(frozen=True)
class FailureKind(Enum):
    TRANSIENT = "transient"
    PERMANENT = "permanent" 

@dataclass(frozen=True)
class FailureReason:
    kind: FailureKind
    message: str
    stage: str