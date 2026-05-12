from .composition import IngestionConfig
import os

def load_ingestion_config_from_env() -> IngestionConfig:
    return IngestionConfig(
        db_url= _required("DB_URL"),
        gemini_api_key= _required("GEMINI_API_KEY"),
        embedding_model= os.getenv("EMBEDDING_MODEL_ID"),
        embedding_size= int(os.getenv("EMBEDDING_SIZE")),
        chunk_size= int(os.getenv("CHUNK_SIZE")),
        overlap_size= int(os.getenv("OVERLAP_SIZE")),
    )

def _required(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise ValueError(f"Environment variable {key} is required")
    return value