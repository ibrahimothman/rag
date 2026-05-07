from src.domains.retrieval.composition import RetrievalConfig
import os

def load_retrieval_config_from_env() -> RetrievalConfig:
    return RetrievalConfig(
        db_url= _required("POSTGRES_URL"),
        gemini_api_key= _required("GEMINI_API_KEY"),
        embedding_model= os.getenv("EMBEDDING_MODEL", "gemini-embedding-2"),
        embedding_size= int(os.getenv("EMBEDDING_SIZE", "1536")),
     
    )

def _required(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise ValueError(f"Environment variable {key} is required")
    return value