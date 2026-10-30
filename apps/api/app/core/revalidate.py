"""On-demand ISR revalidation of public pages (Part 2 §9.4): the API tells the web app which
paths changed (product page, Karu ID pages, maker page) after verification/stock/listing edits."""

from __future__ import annotations

import asyncio
import logging

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings

log = logging.getLogger("karu.revalidate")


async def _post(paths: list[str]) -> None:
    s = get_settings()
    if not s.web_revalidate_secret or not paths:
        return
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            await c.post(f"{s.web_internal_url}/api/revalidate", json={"paths": paths},
                         headers={"x-revalidate-secret": s.web_revalidate_secret})
    except Exception as exc:  # noqa: BLE001 - pages also expire on their own (revalidate window)
        log.info("revalidate failed: %s", exc)


async def revalidate_listing(db: AsyncSession, listing) -> None:  # noqa: ANN001
    from app.modules.artisans.models import ArtisanProfile
    from app.modules.karu_ids.models import KaruId

    profile = await db.get(ArtisanProfile, listing.artisan_id)
    codes = (await db.execute(select(KaruId.code).where(KaruId.listing_id == listing.id))).scalars().all()
    paths = [f"/p/{listing.short_code}", *[f"/k/{c}" for c in codes]]
    if profile:
        paths.append(f"/m/{profile.handle}")
    asyncio.get_event_loop().create_task(_post(paths))


async def revalidate_paths(paths: list[str]) -> None:
    asyncio.get_event_loop().create_task(_post(paths))
