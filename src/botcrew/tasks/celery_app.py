"""Celery application instance for async task processing.

Celery runs as a SEPARATE process from FastAPI. Workers are sync --
never use async code inside Celery tasks. The broker and result backend
both use the same Redis instance as the main application.

Worker startup: celery -A botcrew.tasks.celery_app:celery_app worker --loglevel=info
Beat startup: celery -A botcrew.tasks.celery_app:celery_app beat --scheduler sqlalchemy_celery_beat.schedulers:DatabaseScheduler --loglevel=info
"""

from celery import Celery

from botcrew.config import get_settings

settings = get_settings()

celery_app = Celery(
    "botcrew",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_scheduler="sqlalchemy_celery_beat.schedulers:DatabaseScheduler",
    beat_dburi=settings.celery_beat_dburi,
)

# Auto-discover tasks in the botcrew.tasks package
celery_app.autodiscover_tasks(["botcrew.tasks"])
