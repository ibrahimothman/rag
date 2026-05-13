from uuid import uuid4, UUID

from src.domains.generation.orchestration.pipeline import GenerationPipeline
from src.domains.generation.api import GenerateAnswer
from src.domains.generation.domain import GenerationResult

class GenerationHandler:
    def __init__(self, pipeline: GenerationPipeline):
        self._pipeline = pipeline

    def handle_generate(self, command: GenerateAnswer) -> GenerationResult | None:
        return self._pipeline.run(
            request_id=command.request_id,
            question=command.question,
            grounding=command.grounding
        )
