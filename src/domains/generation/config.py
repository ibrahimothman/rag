from .composition import GenerationConfig
import os

def load_generation_config_from_env() -> GenerationConfig:
    return GenerationConfig(
     
        gemini_api_key= _required("GEMINI_API_KEY"),
        model= _required("GENERATION_MODEL_ID"),
    )

def _required(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise ValueError(f"Environment variable {key} is required")
    return value