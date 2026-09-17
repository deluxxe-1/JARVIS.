from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://aria:aria_secret@postgres:5432/aria"
    
    # Redis
    redis_url: str = "redis://redis:6379/0"
    
    # Ollama
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "qwen3:8b"
    ollama_embedding_model: str = "bge-m3"
    ollama_num_ctx: int = 8192
    ollama_temperature: float = 0.1
    
    # JWT Auth
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 10080  # 7 days
    
    # External APIs
    google_maps_api_key: str = ""
    news_api_key: str = ""
    finnhub_api_key: str = ""
    coingecko_api_url: str = "https://api.coingecko.com/api/v3"
    
    # FCM
    fcm_server_key: str = ""
    
    # App & Security
    log_level: str = "INFO"
    app_name: str = "ARIA"
    cors_origins: list[str] = [
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1",
        "app://aria",
    ]
    
    # Memory
    memory_top_k: int = 8  # Number of memories to retrieve for RAG context
    memory_similarity_threshold: float = 0.3
    
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

@lru_cache()
def get_settings() -> Settings:
    return Settings()
