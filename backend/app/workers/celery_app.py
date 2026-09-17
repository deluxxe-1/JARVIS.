from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "aria",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "check-market-alerts-every-minute": {
            "task": "check_market_alerts",
            "schedule": 60.0,
        },
    },
)

# Auto-discover tasks from workers module
celery_app.autodiscover_tasks(["app.workers"])

from app.workers import price_monitor  # noqa: F401
from app.workers import memory_extractor  # noqa: F401
