import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.init_db import init_db
from app.api.router import api_router
from app.config import get_settings

from app.core.tool_registry import tool_registry
from app.tools.routes import RoutesTool
from app.tools.news import NewsTool
from app.tools.markets import MarketsTool
from app.tools.crypto import CryptoTool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestión del ciclo de vida de la aplicación.
    Inicializa la base de datos al inicio.
    """
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized.")

    logger.info("Registering tools...")
    tool_registry.register(RoutesTool())
    tool_registry.register(NewsTool())
    tool_registry.register(MarketsTool())
    tool_registry.register(CryptoTool())
    logger.info("Tools registered successfully.")
    
    logger.info("Startup complete.")
    yield
    logger.info("Shutting down ARIA application...")

app = FastAPI(
    title='ARIA API',
    version='0.1.0',
    lifespan=lifespan
)

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"^https?://(100\.\d{1,3}\.\d{1,3}\.\d{1,3}|localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

@app.get("/")
async def root():
    """Endpoint raíz que retorna el estado básico de la API."""
    return {"name": "ARIA", "version": "0.1.0", "status": "running"}
