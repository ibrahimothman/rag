
from dataclasses import dataclass

from src.domains.generation.stages import LLMCaller
from src.domains.generation.orchestration import GenerationPipeline, GenerationHandler
from src.domains.generation.infrastructure import GeminiGeneration, GeminiGenerationConfig
from src.shared.event_publishers import InMemoryEventPublisher
from src.shared.gemini import GeminiProviderClientConfig, GeminiProviderClient


@dataclass(frozen=True)
class GenerationConfig:
    """Configuration for the generation system"""
    gemini_api_key: str
    model: str
   
    

def build_generation(
    config: GenerationConfig,
    event_subscribers: list | None = None,
)-> GenerationHandler:

    gemini_provider_client = GeminiProviderClient(GeminiProviderClientConfig(
        api_key=config.gemini_api_key,
    ))
    generation_model = GeminiGeneration(GeminiGenerationConfig(
        model=config.model
    ), gemini_provider_client)

    llm_caller = LLMCaller(generation_model)
    
    event_publisher = InMemoryEventPublisher(
        subscribers=event_subscribers or [],
    )

    pipeline = GenerationPipeline(
        llm_caller=llm_caller,
        events=event_publisher,
    )


    handler = GenerationHandler(pipeline)
    return handler



