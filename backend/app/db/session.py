from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from pgvector.sqlalchemy import Vector  # noqa: F401 - Ensure pgvector is available
from app.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Alias for workers that create sessions outside of FastAPI's DI
async_session_factory = AsyncSessionLocal

Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yields an AsyncSession for database operations."""
    async with AsyncSessionLocal() as session:
        yield session
