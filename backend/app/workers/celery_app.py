from celery import Celery
from app.core.config import settings

celery_app = Celery("signalflow", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "refresh-system-heartbeat": {
            "task": "app.workers.tasks.heartbeat",
            "schedule": 300.0,
        }
    },
)
celery_app.autodiscover_tasks(["app.workers"])
