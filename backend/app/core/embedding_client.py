import logging
import httpx
from app.config import get_settings

logger = logging.getLogger(__name__)

class EmbeddingClient:
    """Async client for generating embeddings via Ollama."""
    
    def __init__(self):
        settings = get_settings()
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_embedding_model
    
    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        url = f"{self.base_url}/api/embed"
        payload = {
            "model": self.model,
            "input": text
        }
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data["embeddings"][0]
            except Exception as e:
                logger.error(f"Error generating embedding: {e}")
                raise
    
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        url = f"{self.base_url}/api/embed"
        payload = {
            "model": self.model,
            "input": texts
        }
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data["embeddings"]
            except Exception as e:
                logger.error(f"Error generating batch embeddings: {e}")
                raise
    
    async def is_available(self) -> bool:
        """Check if the embedding model is available."""
        url = f"{self.base_url}/api/tags"
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                return True
            except Exception as e:
                logger.error(f"Ollama embedding availability check failed: {e}")
                return False
