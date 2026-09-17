import logging
from sqlalchemy import text
from app.db.session import engine, Base

logger = logging.getLogger(__name__)

async def init_db() -> None:
    """
    Initialize the database by creating tables and enabling pgvector.
    Crea las tablas y activa la extensión vector.
    """
    try:
        async with engine.begin() as conn:
            # Enable pgvector extension
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Successfully initialized database tables and pgvector extension.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise
