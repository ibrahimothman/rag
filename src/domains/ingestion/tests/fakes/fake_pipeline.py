from ...domain.job import IngestionJob
from typing import Callable



class FakePipeline:

    def __init__(self):
        self.behavior: Callable[[IngestionJob], None] = lambda job: None
        self.run_count = 0

    def run(self, job: IngestionJob, source_file) -> None:
        self.run_count += 1
        self.behavior(job)
        



# pipline.run(job, source) -> None:
# _make_complete_job(job)
   

        