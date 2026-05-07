class IngestionJobError(Exception):
    """Base for all IngestionJob rules violations"""

class IlligalStageTransition(IngestionJobError):
    pass

class JobNotRetryable(IngestionJobError):
    pass