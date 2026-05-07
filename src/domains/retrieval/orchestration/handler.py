from src.domains.retrieval.orchestration.pipeline import RetrievalPipeline
from src.domains.retrieval.api.commands import RetrieveRelevantChunks
from src.domains.retrieval.domain.result import RetrievalResult

class RetrievalHandler:

    def __init__(self, pipeline: RetrievalPipeline):
        self._pipeline = pipeline

    def handle_retrieve(self, command: RetrieveRelevantChunks) -> RetrievalResult | None:

        return self._pipeline.run(
            request_id=command.request_id,
            query_text=command.query_text
        )