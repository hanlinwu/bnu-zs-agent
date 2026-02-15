"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery = Celery(
    "bnu_admission",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
)

celery.conf.beat_schedule = {
    "refresh-calendar-daily": {
        "task": "app.tasks.cleanup_task.refresh_calendar",
        "schedule": crontab(hour=0, minute=0),
    },
    "cleanup-expired-daily": {
        "task": "app.tasks.cleanup_task.cleanup_expired",
        "schedule": crontab(hour=3, minute=0),
    },
    "archive-logs-weekly": {
        "task": "app.tasks.cleanup_task.archive_logs",
        "schedule": crontab(day_of_week=0, hour=4),
    },
}

celery.autodiscover_tasks(["app.tasks"])
