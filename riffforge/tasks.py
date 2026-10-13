"""Redis delivery plus durable database reconciliation after a broker outage."""

import os

from celery import Celery

from .worker import run_once

celery = Celery(
    "riffforge", broker=os.environ.get("RIFFFORGE_BROKER", "redis://redis:6379/0")
)
celery.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    task_serializer="json",
    accept_content=["json"],
    broker_transport_options={"visibility_timeout": 300},
    beat_schedule={
        "reconcile-durable-queue": {"task": "riffforge.drain", "schedule": 10.0}
    },
)


@celery.task(name="riffforge.process", soft_time_limit=240, time_limit=270)
def process(job_id):
    return run_once(job_id)


@celery.task(name="riffforge.drain", soft_time_limit=240, time_limit=270)
def drain():
    return run_once()
