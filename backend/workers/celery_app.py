from celery import Celery

from core.config import settings

celery_app = Celery("pusula", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    broker_transport_options={"visibility_timeout": 3600},
    task_time_limit=1800,
    task_soft_time_limit=1740,
    worker_prefetch_multiplier=1,
    task_routes={"pusula.*": {"queue": "pusula"}},
    beat_schedule={
        "cleanup-expired-visitors": {
            "task": "pusula.cleanup_expired_visitors",
            "schedule": 86400.0,
        },
    },
)
celery_app.autodiscover_tasks(["workers"])
