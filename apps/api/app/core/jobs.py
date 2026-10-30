"""Background jobs (Part 2 §1 "all slow or external work runs in workers").

Every job is a row in `jobs` (so the web app can stream progress over SSE) plus a handler
registered with `@handler("type")`. Dispatch happens after the enqueuing transaction
commits:
- TASK_MODE=celery → `karu.run_job` on the queue for that job type (Redis broker);
- TASK_MODE=inline → an asyncio task inside the API process (local dev, demo laptop).
Periodic work (reservation expiry, payout holds, price refresh …) is registered with
`@periodic(name, every_s)` and run by Celery Beat or by the in-process scheduler.
"""

from __future__ import annotations

import asyncio
import logging
import traceback
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import sessionmaker, utcnow

log = logging.getLogger("karu.jobs")

Handler = Callable[[AsyncSession, "object"], Awaitable[dict | None]]


@dataclass
class HandlerSpec:
    fn: Handler
    queue: str
    max_attempts: int
    timeout_s: int


HANDLERS: dict[str, HandlerSpec] = {}
PERIODIC: dict[str, tuple[Callable[[AsyncSession], Awaitable[None]], int]] = {}
_inflight: set[asyncio.Task] = set()


def handler(job_type: str, *, queue: str = "default", max_attempts: int = 3, timeout_s: int = 900):
    def deco(fn: Handler) -> Handler:
        HANDLERS[job_type] = HandlerSpec(fn, queue, max_attempts, timeout_s)
        return fn

    return deco


def periodic(name: str, every_s: int):
    def deco(fn):
        PERIODIC[name] = (fn, every_s)
        return fn

    return deco


async def enqueue(
    db: AsyncSession,
    job_type: str,
    *,
    ref_type: str | None = None,
    ref_id: str | None = None,
    owner_user_id: uuid.UUID | None = None,
    payload: dict | None = None,
    delay_s: int = 0,
):
    from app.modules.jobs.models import Job

    job = Job(
        type=job_type,
        ref_type=ref_type,
        ref_id=str(ref_id) if ref_id else None,
        owner_user_id=owner_user_id,
        payload=payload or {},
        run_after=utcnow() + timedelta(seconds=delay_s) if delay_s else None,
    )
    db.add(job)
    await db.flush()
    pending = db.sync_session.info.setdefault("karu_pending_jobs", [])
    spec = HANDLERS.get(job_type)
    pending.append((job.id, delay_s, spec.queue if spec else "default"))
    if not db.sync_session.info.get("karu_hook"):
        db.sync_session.info["karu_hook"] = True
        event.listen(db.sync_session, "after_commit", _after_commit)
        event.listen(db.sync_session, "after_rollback", _after_rollback)
    return job


def _after_commit(session) -> None:  # noqa: ANN001
    pending = session.info.pop("karu_pending_jobs", [])
    for job_id, delay, queue in pending:
        dispatch(job_id, delay, queue)


def _after_rollback(session) -> None:  # noqa: ANN001
    session.info.pop("karu_pending_jobs", None)


def dispatch(job_id: uuid.UUID, delay_s: int = 0, queue: str = "default") -> None:
    s = get_settings()
    if s.task_mode == "celery":
        from app.workers.celery_app import send_job

        send_job(job_id, delay_s, queue)
        return
    loop = asyncio.get_event_loop()
    task = loop.create_task(_run_later(job_id, delay_s))
    if not delay_s:
        _inflight.add(task)
        task.add_done_callback(_inflight.discard)


async def _run_later(job_id: uuid.UUID, delay_s: int) -> None:
    if delay_s:
        await asyncio.sleep(delay_s)
    await run_job(job_id)


async def drain(timeout: float = 60.0) -> None:
    """Wait for in-process jobs (tests, scripts)."""
    deadline = asyncio.get_event_loop().time() + timeout
    while _inflight:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            raise TimeoutError("jobs did not finish")
        await asyncio.wait(list(_inflight), timeout=remaining)


async def set_progress(db: AsyncSession, job, progress: int, step: str | None = None, *, log_step: bool = False) -> None:
    job.progress = max(0, min(100, progress))
    if step:
        job.step = step
        if log_step:
            job.steps = [*(job.steps or []), {"at": utcnow().isoformat(), "step": step}]
    await db.commit()


async def run_job(job_id: uuid.UUID) -> None:
    from app.modules.jobs.models import Job

    async with sessionmaker()() as db:
        job = await db.get(Job, job_id)
        if job is None or job.status in ("completed", "running"):
            return
        spec = HANDLERS.get(job.type)
        if spec is None:
            job.status, job.error = "failed", f"no handler for {job.type}"
            await db.commit()
            return
        job.status = "running"
        job.started_at = utcnow()
        job.attempts += 1
        await db.commit()
        try:
            result = await asyncio.wait_for(spec.fn(db, job), timeout=spec.timeout_s)
            await db.refresh(job)
            job.status = "completed"
            job.progress = 100
            job.result = result or {}
            job.finished_at = utcnow()
            await db.commit()
        except Exception as exc:  # noqa: BLE001
            log.exception("job %s (%s) failed", job_id, job.type if job else "?")
            await db.rollback()
            job = await db.get(Job, job_id)
            assert job is not None
            job.error = f"{type(exc).__name__}: {exc}"[:2000]
            if job.attempts < spec.max_attempts and not isinstance(exc, PermanentJobError):
                job.status = "queued"
                backoff = 2 ** job.attempts * (5 if get_settings().is_dev else 60)
                await db.commit()
                dispatch(job.id, backoff, spec.queue)
            else:
                job.status = "failed"
                job.finished_at = utcnow()
                job.result = {"traceback": traceback.format_exc()[-4000:]}
                await db.commit()
                fail_hook = FAILURE_HOOKS.get(job.type)
                if fail_hook:
                    try:
                        await fail_hook(db, job)
                        await db.commit()
                    except Exception:  # noqa: BLE001
                        log.exception("failure hook for %s failed", job.type)


class PermanentJobError(Exception):
    """Raise from a handler to fail without retries."""


FAILURE_HOOKS: dict[str, Callable[[AsyncSession, object], Awaitable[None]]] = {}


def on_failure(job_type: str):
    def deco(fn):
        FAILURE_HOOKS[job_type] = fn
        return fn

    return deco


async def run_periodic(name: str) -> None:
    fn, _ = PERIODIC[name]
    async with sessionmaker()() as db:
        try:
            await fn(db)
            await db.commit()
        except Exception:  # noqa: BLE001
            log.exception("periodic %s failed", name)
            await db.rollback()


async def scheduler_loop(stop: asyncio.Event) -> None:
    """In-process replacement for Celery Beat (TASK_MODE=inline)."""
    last: dict[str, float] = {}
    loop = asyncio.get_event_loop()
    await asyncio.sleep(3)
    while not stop.is_set():
        now = loop.time()
        for name, (_, every) in PERIODIC.items():
            if now - last.get(name, -1e9) >= every:
                last[name] = now
                await run_periodic(name)
        try:
            await asyncio.wait_for(stop.wait(), timeout=15)
        except TimeoutError:
            pass


async def resume_pending() -> None:
    """On API start in inline mode, pick up jobs left queued by a previous process."""
    from sqlalchemy import select

    from app.modules.jobs.models import Job

    async with sessionmaker()() as db:
        rows = (await db.execute(select(Job).where(Job.status.in_(["queued", "running"])))).scalars().all()
        for job in rows:
            job.status = "queued"
        await db.commit()
        for job in rows:
            spec = HANDLERS.get(job.type)
            dispatch(job.id, 1, spec.queue if spec else "default")
