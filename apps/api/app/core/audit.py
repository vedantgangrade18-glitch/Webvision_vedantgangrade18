"""Audit log and external-call accounting helpers."""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import sessionmaker, utcnow


async def audit(
    db: AsyncSession,
    actor_user_id: uuid.UUID | None,
    action: str,
    target_type: str | None = None,
    target_id: str | None = None,
    before: dict | None = None,
    after: dict | None = None,
    reason: str | None = None,
    ip_hash: str | None = None,
) -> None:
    from app.modules.admin.models import AuditLog

    db.add(
        AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            target_type=target_type,
            target_id=str(target_id) if target_id else None,
            before=before,
            after=after,
            reason=reason,
            ip_hash=ip_hash,
        )
    )


async def record_call(
    provider: str,
    operation: str,
    *,
    status: str,
    latency_ms: int,
    cost_inr: float | Decimal = 0,
    listing_id: uuid.UUID | None = None,
    run_id: uuid.UUID | None = None,
    error: str | None = None,
) -> None:
    """External calls are logged in their own short transaction so failures are kept."""
    from app.modules.admin.models import ExternalCall

    async with sessionmaker()() as db:
        db.add(
            ExternalCall(
                provider=provider,
                operation=operation,
                status=status,
                latency_ms=latency_ms,
                cost_inr=Decimal(str(cost_inr)),
                listing_id=listing_id,
                run_id=run_id,
                error=(error or "")[:255] or None,
            )
        )
        await db.commit()


@asynccontextmanager
async def track_call(
    provider: str, operation: str, *, cost_inr: float = 0, listing_id=None, run_id=None
) -> AsyncIterator[None]:
    start = time.perf_counter()
    try:
        yield
    except Exception as exc:
        await record_call(
            provider, operation, status="error", latency_ms=int((time.perf_counter() - start) * 1000),
            listing_id=listing_id, run_id=run_id, error=f"{type(exc).__name__}: {exc}",
        )
        raise
    await record_call(
        provider, operation, status="ok", latency_ms=int((time.perf_counter() - start) * 1000),
        cost_inr=cost_inr, listing_id=listing_id, run_id=run_id,
    )


async def spent_today(db: AsyncSession, provider: str) -> Decimal:
    from app.modules.admin.models import ExternalCall

    start = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    total = (
        await db.execute(
            select(func.coalesce(func.sum(ExternalCall.cost_inr), 0)).where(
                ExternalCall.provider == provider, ExternalCall.at >= start
            )
        )
    ).scalar_one()
    return Decimal(str(total))


async def within_budget(db: AsyncSession, provider: str) -> bool:
    from app.core.appconfig import get_config

    budgets = await get_config(db, "budgets.v1")
    limit = budgets.get(f"{provider}_daily_inr")
    if limit is None:
        return True
    return await spent_today(db, provider) < Decimal(str(limit))
