"""[DEMO] Zero-form marketplace syndication with the TinyFish Agent (Part 2 §8.4).

Uses only team-owned demo seller accounts (credentials referenced from the secrets manager,
never artisans' credentials). Steps stream to A20 via the job's step log.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_db, utcnow
from app.core.deps import current_artisan
from app.core.errors import AppError
from app.core.i18n import pick_lang
from app.core.jobs import handler, set_progress
from app.modules.catalog import attributes
from app.modules.catalog.models import Category, Listing
from app.modules.catalog.service import gallery
from app.modules.syndication.models import SyndicationJob
from app.providers.webintel import AgentStep, get_webintel

PORTALS = {
    "ondc": {"name": "ONDC seller app (demo)", "url": "https://demo-seller.example.com/ondc"},
    "indiamart": {"name": "IndiaMART (demo seller)", "url": "https://seller.indiamart.com/"},
    "coop": {"name": "Co-op storefront (demo)", "url": "https://demo-coop.example.com/admin"},
}

router = APIRouter(tags=["syndication"])


@handler("agents.syndicate", queue="agents", max_attempts=1, timeout_s=900)
async def syndicate(db: AsyncSession, job) -> dict:
    sj = await db.get(SyndicationJob, uuid.UUID(job.payload["syndication_id"]))
    listing = await db.get(Listing, sj.listing_id)
    category = await db.get(Category, listing.category_id) if listing.category_id else None
    portal = PORTALS[sj.portal]
    sj.status = "running"
    await set_progress(db, job, 5, f"Opening {portal['name']}", log_step=True)
    pics = await gallery(db, listing)
    data = {
        "title": pick_lang(listing.title, "en")[0], "description": pick_lang(listing.description, "en")[0],
        "price_inr": float(listing.price_inr or 0), "category": category.slug if category else "other",
        "attributes": attributes.for_category(category.attribute_schema if category else None, listing.attributes),
        "image_url": pics[0]["jpg"] if pics else None, "karu_link": f"{get_settings().public_base_url}/p/{listing.short_code}",
    }
    progress = [10]

    async def on_step(step: AgentStep) -> None:
        if step.kind == "streaming_url":
            sj.streaming_url = step.data.get("url")
        progress[0] = min(95, progress[0] + 9)
        sj.steps = [*(sj.steps or []), {"at": utcnow().isoformat(), "step": step.message, "kind": step.kind}]
        await set_progress(db, job, progress[0], step.message, log_step=True)

    goal = (f"You are on the seller dashboard of {portal['name']} using the team's demo seller account "
            "(already signed in through the saved browser profile). "
            "open 'Add product', fill every field from the inputs (title, description, price in INR, category, attributes), "
            "upload the image from image_url, add the karu_link in the description, submit, and return JSON "
            '{"result_url": "<url of the new listing>"}.')
    result = await get_webintel().run_agent(goal, start_url=portal["url"], inputs=data, on_step=on_step, listing_id=listing.id,
                                            profile_id=get_settings().demo_syndication_credentials_ref or None)
    payload = result.result if isinstance(result.result, dict) else {}
    if result.status == "COMPLETED" and payload.get("result_url"):
        sj.status, sj.result_url = "completed", payload["result_url"]
    else:
        sj.status = "failed"
        sj.steps = [*(sj.steps or []), {"at": utcnow().isoformat(), "step": f"Failed: {result.error or 'no result'}", "kind": "error"}]
    await db.commit()
    if sj.status == "failed":
        raise AppError(502, "agent_failed")
    return {"result_url": sj.result_url}


@router.get("/syndication/{syndication_id}")
async def get_syndication(syndication_id: str, artisan=Depends(current_artisan), db: AsyncSession = Depends(get_db)):
    sj = await db.get(SyndicationJob, uuid.UUID(syndication_id))
    listing = await db.get(Listing, sj.listing_id) if sj else None
    if sj is None or listing is None or listing.artisan_id != artisan.id:
        raise AppError(404, "not_found")
    return {"id": str(sj.id), "portal": sj.portal, "portal_name": PORTALS[sj.portal]["name"], "status": sj.status,
            "steps": sj.steps, "result_url": sj.result_url, "streaming_url": sj.streaming_url,
            "job_id": str(sj.job_id) if sj.job_id else None}
