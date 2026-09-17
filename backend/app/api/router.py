from fastapi import APIRouter
from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.memory import router as memory_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health_router, prefix="/health")
api_router.include_router(auth_router, prefix="/auth")
api_router.include_router(chat_router, prefix="/chat")
api_router.include_router(memory_router, prefix="/memory")
