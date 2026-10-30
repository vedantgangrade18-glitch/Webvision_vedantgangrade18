"""Job progress: `GET /jobs/{id}` and Server-Sent Events `GET /jobs/{id}/events` (Part 2 §9.5).

SSE polls the `jobs` row (works for in-process and Celery workers alike); clients fall back
to polling `GET /jobs/{id}` every 3 s.
"""

from __future__ import annotations

import asyncio
import json
import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db, sessionmaker
from app.core.deps import STAFF_ROLES, current_user
from app.core.errors import AppError
from app.modules.jobs.models import Job

router = APIRouter(tags=["jobs"])


def job_out(j: Job) -> dict:
    return {"id": str(j.id), "type": j.type, "status": j.status, "progress": j.progress, "step": j.step,
            "steps": j.steps[-30:] if j.steps else [], "result_ref": {"type": j.ref_type, "id": j.ref_id},
            "error": j.error if j.status == "failed" else None,
            "result": {k: v for k, v in (j.result or {}).items() if k != "traceback"}}


async def _visible(db: AsyncSession, job_id: str, user) -> Job:
    try:
        job = await db.get(Job, uuid.UUID(job_id))
    except ValueError:
        job = None
    if job is None or (job.owner_user_id != user.id and not set(user.roles) & STAFF_ROLES):
        raise AppError(404, "job_not_found")
    return job


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    return job_out(await _visible(db, job_id, user))


@router.get("/jobs/{job_id}/events")
async def job_events(job_id: str, request: Request, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    job = await _visible(db, job_id, user)
    jid = job.id

    async def stream():
        last = None
        idle = 0
        while True:
            if await request.is_disconnected():
                break
            async with sessionmaker()() as s:
                j = await s.get(Job, jid)
                data = job_out(j)
            snapshot = json.dumps(data, sort_keys=True)
            if snapshot != last:
                last = snapshot
                idle = 0
                yield f"event: progress\ndata: {snapshot}\n\n"
            else:
                idle += 1
                if idle % 15 == 0:
                    yield ": keep-alive\n\n"
            if data["status"] in ("completed", "failed"):
                yield f"event: done\ndata: {snapshot}\n\n"
                break
            await asyncio.sleep(1)

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
