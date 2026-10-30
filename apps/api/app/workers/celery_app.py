"""Celery workers + Beat (TASK_MODE=celery). Queues per job type (Part 2 §12):
ai · verification · pricing · media · notify · agents · default.

    celery -A app.workers.celery_app worker -Q ai,verification,pricing,media,notify,agents,default
    celery -A app.workers.celery_app beat
"""

from __future__ import annotations

import asyncio
import uuid

from celery import Celery

from app.core.config import get_settings

settings = get_settings()
celery = Celery("karu", broker=settings.redis_url or "redis://localhost:6379/0")
celery.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_queue="default",
    broker_connection_retry_on_startup=True,
    timezone="Asia/Kolkata",
)


def _load_handlers() -> None:
    import app.main  # noqa: F401  (registers models, job handlers and periodic tasks)


async def _with_fresh_engine(coro_factory):
    """asyncio.run() makes a new loop per task: give each run its own NullPool engine."""
    from app.core.db import configure_engine, get_engine

    configure_engine(settings.database_url, null_pool=True)
    try:
        await coro_factory()
    finally:
        await get_engine().dispose()


@celery.task(name="karu.run_job")
def run_job_task(job_id: str) -> None:
    from app.core import jobs

    _load_handlers()
    asyncio.run(_with_fresh_engine(lambda: jobs.run_job(uuid.UUID(job_id))))


@celery.task(name="karu.periodic")
def periodic_task(name: str) -> None:
    from app.core import jobs

    _load_handlers()
    asyncio.run(_with_fresh_engine(lambda: jobs.run_periodic(name)))


def send_job(job_id: uuid.UUID, delay_s: int = 0, queue: str = "default") -> None:
    run_job_task.apply_async(args=[str(job_id)], countdown=delay_s or None, queue=queue)


def _beat_schedule() -> dict:
    _load_handlers()
    from app.core.jobs import PERIODIC

    return {name: {"task": "karu.periodic", "schedule": float(every), "args": [name], "options": {"queue": "default"}}
            for name, (_, every) in PERIODIC.items()}


celery.conf.beat_schedule = _beat_schedule()
