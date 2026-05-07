from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4

from .failure import FailureReason, RetryPolicy
from .exceptions import IlligalStageTransition, JobNotRetryable
from .stages import IngestionStage




_NEXT_STAGE = {
    IngestionStage.QUEUED: IngestionStage.EXTRACTING,
    IngestionStage.EXTRACTING: IngestionStage.CHUNKING,
    IngestionStage.CHUNKING: IngestionStage.EMBEDDING,
    IngestionStage.EMBEDDING: IngestionStage.INDEXING,
    IngestionStage.INDEXING: IngestionStage.COMPLETED,
}

TERMINAL_STATES = {IngestionStage.COMPLETED, IngestionStage.FAILED}

@dataclass
class IngestionJob:
    id: UUID
    document_id: UUID
    stage: IngestionStage = IngestionStage.QUEUED
    attempts: int = 1
    failure: FailureReason | None = None
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy.default)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))



    @classmethod
    def create(cls, document_id: UUID, retry_policy: RetryPolicy | None = None) -> "IngestionJob":
        return IngestionJob(
            id=uuid4(),
            document_id=document_id,
            retry_policy=retry_policy or RetryPolicy.default(),
        )

    def advance_to(self, next_stage: IngestionStage) -> None:
        """ enforce valid transitions """

        # Rule 1: Cannot advance from terminal states
        if self.stage in TERMINAL_STATES:
            raise IlligalStageTransition(f"Cannot advance from terminal state {self.stage.value}")

        # Rule 2: Cannot advance to an invalid stage
        expected_stage = _NEXT_STAGE[self.stage]    
        if next_stage != expected_stage:
            raise IlligalStageTransition(f"Cannot advance from {self.stage.value} to {next_stage.value}. "
            f"Expected {expected_stage.value if expected_stage else 'none'}.")

        # Rule 3: advancing clears any prior failures
        self.failure = None
        self.stage = next_stage
        self.updated_at = datetime.now(timezone.utc)

    def mark_failed(self, reason: FailureReason) -> None:
        """ records why, allows retry """

        # Rule 1: Cannot fail a job that is already completed
        if self.stage == IngestionStage.COMPLETED:
            raise IlligalStageTransition(f"Cannot fail a completed job")

        # Rule 2: the failure's stage must match the current stage
        if reason.stage != self.stage:
            raise IlligalStageTransition(f"Failure stage {reason.stage.value} does not match current stage {self.stage.value}")

        self.failure = reason
        self.stage = IngestionStage.FAILED
        self.updated_at = datetime.now(timezone.utc)

    def retry(self):
        """ Reset the job to retry from the stage it failed at """

        # Rule 1: only failed jobs can be retried
        if self.stage != IngestionStage.FAILED:
            raise IlligalStageTransition(f"Cannot retry a job that is in stage {self.stage.value}; must be FAILED")

        # Rule 2: the failure must be retryable
        if self.failure is None or not self.failure.is_retryable:
            raise JobNotRetryable(f"Failure {self.failure.kind.value} is not retryable (permanent, or missing failure reason)")

        # Rule 3: respect the retry policy's attempt limit
        if self.attempts >= self.retry_policy.max_attempts:
            raise JobNotRetryable(f"Job has reached the maximum number of retries ({self.attempts}/{self.retry_policy.max_attempts})")

        # Resume from the stage it failed at not frm the beginning
        self.stage = IngestionStage.QUEUED
        self.failure = None
        self.attempts += 1
        self.updated_at = datetime.now(timezone.utc)