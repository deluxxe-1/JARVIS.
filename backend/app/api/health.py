import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import httpx
from redis import asyncio as aioredis
from app.db.session import get_db
from app.config import get_settings

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint.
    Verifica el estado de conexión de la BD, Redis y Ollama.
    """
    settings = get_settings()
    
    status = {
        "status": "running",
        "db_connected": False,
        "redis_connected": False,
        "ollama_connected": False
    }
    
    # Check DB
    try:
        await db.execute(text("SELECT 1"))
        status["db_connected"] = True
    except Exception as e:
        logger.error(f"DB health check failed: {e}")
        
    # Check Redis
    try:
        redis = await aioredis.from_url(settings.redis_url)
        await redis.ping()
        await redis.aclose()
        status["redis_connected"] = True
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        
    # Check Ollama
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            if resp.status_code == 200:
                status["ollama_connected"] = True
    except Exception as e:
        logger.error(f"Ollama health check failed: {e}")
        
    return status
