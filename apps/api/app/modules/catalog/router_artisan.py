from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.appconfig import flag, get_config
from app.core.db import get_db, utcnow
from app.core.deps import current_artisan, current_user, locale_dep
from app.core.errors import AppError, bad_request, not_found
from app.core.i18n import LOCALES, pick_lang, t
from app.core.jobs import enqueue
from app.core.revalidate import revalidate_listing
from app.modules.ai_pipeline import service as _ai  # noqa: F401  (registers job handlers)
from app.modules.artisans.models import ArtisanProfile
from app.modules.catalog import attributes
from app.modules.catalog.models import AiExtraction, Category, Craft, Listing, ListingMedia
from app.modules.catalog.service import (
    CORE_ATTRIBUTES,
    category_by_slug,
    craft_by_slug,
    create_karu_ids,
    gallery,
    latest_run,
    listing_media,
    primary_images,
    refresh_search,
    save_version,
    stock_state,
    sync_quantity,
    unique_short_code,
)
from app.modules.karu_ids.models import KaruId, KaruIdEvent
from app.modules.karu_ids.service import share_image, short_url, tag_sheet, unit_url
from app.modules.media.service import owned_media
from app.modules.pricing.service import advice_view
from app.modules.verification.engine import start_run

router = APIRouter(tags=["listings"])


class DraftIn(BaseModel):
    photo_media_ids: list[str] = Field(default_factory=list, max_length=6)
    voice_media_id: str | None = None
    client_transcript: str | None = Field(default=None, max_length=4000)
    source_lang: str | None = None
    manual: bool = False  # extraction-free manual form (F2 fallback)


@router.post("/listings")
async def create_draft(body: DraftIn, user=Depends(current_user), artisan: ArtisanProfile = Depends(current_artisan),
                       db: AsyncSession = Depends(get_db)):
    limits = await get_config(db, "limits.v1")
    if not body.photo_media_ids:
        raise bad_request("photo_required")
    if len(body.photo_media_ids) > limits["photos_max"]:
        raise bad_request("too_many_photos", max=limits["photos_max"])
    photos = [await owned_media(db, mid, user.id, {"photo"}) for mid in body.photo_media_ids]
    voice = await owned_media(db, body.voice_media_id, user.id, {"voice"}) if body.voice_media_id else None
    if voice and voice.duration_s and voice.duration_s > limits["voice_note_max_s"] + 5:
        raise bad_request("voice_too_long", max_s=limits["voice_note_max_s"])
    src = body.source_lang if body.source_lang in LOCALES else user.locale
    listing = Listing(artisan_id=artisan.id, short_code=await unique_short_code(db), status="processing",
                      source_lang=src, title={}, description={}, attributes={}, tags=[])
    db.add(listing)
    await db.flush()
    for i, m in enumerate(photos):
        db.add(ListingMedia(listing_id=listing.id, media_id=m.id, role="photo", position=i, is_primary=i == 0))
    if voice:
        db.add(ListingMedia(listing_id=listing.id, media_id=voice.id, role="voice_note"))
    job = await enqueue(db, "ai.process_listing", ref_type="listing", ref_id=str(listing.id), owner_user_id=user.id,
                        payload={"client_transcript": body.client_transcript, "manual": body.manual})
    await db.commit()
    return {"listing_id": str(listing.id), "job_id": str(job.id), "short_code": listing.short_code}


@router.get("/listings/mine")
async def my_listings(status: str | None = None, locale: str = Depends(locale_dep),
                      artisan: ArtisanProfile = Depends(current_artisan), db: AsyncSession = Depends(get_db)):
    q = select(Listing).where(Listing.artisan_id == artisan.id, Listing.status != "deleted")
    if status:
        q = q.where(Listing.status == status)
    rows = list((await db.execute(q.order_by(desc(Listing.updated_at)))).scalars())
    images = await primary_images(db, [li.id for li in rows])
    commerce = await get_config(db, "commerce.v1")
    return {"items": [{
        "id": str(li.id), "code": li.short_code, "status": li.status, "title": pick_lang(li.title, locale)[0],
        "price_inr": float(li.price_inr) if li.price_inr is not None else None, "image": images.get(li.id),
        "stock": stock_state(li.quantity_available, commerce["low_stock_threshold"]),
        "quantity_total": li.quantity_total, "verification": li.verification_status,
        "price_position": li.price_position, "views": li.views_count, "updated_at": li.updated_at.isoformat(),
    } for li in rows]}


async def _owned(db: AsyncSession, listing_id: str, artisan: ArtisanProfile) -> Listing:
    try:
        lid = uuid.UUID(listing_id)
    except ValueError:
        raise AppError(404, "listing_not_found") from None
    listing = await db.get(Listing, lid)
    if listing is None or listing.artisan_id != artisan.id or listing.status == "deleted":
        raise AppError(404, "listing_not_found")
    return listing


async def artisan_view(db: AsyncSession, listing: Listing, locale: str) -> dict:
    from app.modules.jobs.models import Job
    from app.modules.orders.models import OrderItem

    category = await db.get(Category, listing.category_id) if listing.category_id else None
    craft = await db.get(Craft, listing.craft_id) if listing.craft_id else None
    commerce = await get_config(db, "commerce.v1")
    ext = (await db.execute(select(AiExtraction).where(AiExtraction.listing_id == listing.id)
                            .order_by(desc(AiExtraction.created_at)).limit(1))).scalar_one_or_none()
    job = (await db.execute(select(Job).where(Job.ref_id == str(listing.id), Job.type == "ai.process_listing")
                            .order_by(desc(Job.created_at)).limit(1))).scalar_one_or_none()
    shots_job = (await db.execute(select(Job).where(Job.ref_id == str(listing.id), Job.type == "ai.generate_shots")
                                  .order_by(desc(Job.created_at)).limit(1))).scalar_one_or_none()
    if shots_job is None and listing.status == "draft":
        all_lm = await listing_media(db, listing.id)
        has_real_photos = any(lm.role == "photo" for lm, _ in all_lm)
        has_ai_shots = any((lm.role or "").startswith("ai_") for lm, _ in all_lm)
        if has_real_photos and not has_ai_shots:
            profile = await db.get(ArtisanProfile, listing.artisan_id)
            shots_job = await enqueue(db, "ai.generate_shots", ref_type="listing", ref_id=str(listing.id),
                                      owner_user_id=profile.user_id if profile else None)
            await db.commit()
    vids = await listing_media(db, listing.id, ("making_video",))
    sold = (await db.execute(select(func.count(), func.coalesce(func.sum(OrderItem.unit_price), 0)).where(
        OrderItem.listing_id == listing.id, OrderItem.fulfilment_status.in_(["to_pack", "shipped", "delivered"])))).one()
    from app.core.storage import get_storage

    vmedia = vids[-1][1] if vids else None
    return {
        "id": str(listing.id), "code": listing.short_code, "status": listing.status, "source_lang": listing.source_lang,
        "title": listing.title, "description": listing.description, "attributes": listing.attributes, "tags": listing.tags,
        "price_inr": float(listing.price_inr) if listing.price_inr is not None else None,
        "category_slug": category.slug if category else None, "craft_slug": craft.slug if craft else None,
        "returnable": listing.returnable, "shipping": listing.shipping,
        "quantity_total": listing.quantity_total, "quantity_available": listing.quantity_available,
        "stock": stock_state(listing.quantity_available, commerce["low_stock_threshold"]),
        "verification_status": listing.verification_status, "price_position": listing.price_position,
        "field_confidence": listing.field_confidence, "missing_fields": listing.missing_fields,
        "notes_for_artisan": listing.notes_for_artisan,
        "transcript": (ext.transcript or {}).get("text") if ext and ext.transcript else None,
        "transcript_provider": (ext.transcript or {}).get("provider") if ext and ext.transcript else None,
        "extraction_status": ext.status if ext else None,
        "processing": {"job_id": str(job.id), "status": job.status, "progress": job.progress, "step": job.step} if job else None,
        "shots_job_id": str(shots_job.id) if shots_job else None,
        "gallery": await gallery(db, listing),
        "making_video": {"id": str(vmedia.id), "duration_s": vmedia.duration_s,
                         "poster": get_storage().public_url(vmedia.variants["poster.jpg"]) if (vmedia.variants or {}).get("poster.jpg") else None}
        if vmedia else None,
        "views": listing.views_count, "shares": listing.share_count,
        "sales": {"units": sold[0], "revenue_inr": float(sold[1])},
        "share_url": short_url(listing), "published_at": listing.published_at.isoformat() if listing.published_at else None,
        "regenerate_left": await _regen_left(db, listing),
    }


async def _regen_left(db: AsyncSession, listing: Listing) -> int:
    limit = (await get_config(db, "limits.v1"))["regenerate_per_listing_per_day"]
    today = utcnow().date().isoformat()
    used = listing.regenerate_count if listing.regenerate_day == today else 0
    return max(0, limit - used)


@router.get("/listings/{listing_id}")
async def get_listing(listing_id: str, locale: str = Depends(locale_dep), artisan: ArtisanProfile = Depends(current_artisan),
                      db: AsyncSession = Depends(get_db)):
    return await artisan_view(db, await _owned(db, listing_id, artisan), locale)


@router.delete("/listings/{listing_id}/shots/{media_id}")
async def delete_shot(listing_id: str, media_id: str, artisan: ArtisanProfile = Depends(current_artisan),
                      db: AsyncSession = Depends(get_db)):
    listing = await _owned(db, listing_id, artisan)
    try:
        mid = uuid.UUID(media_id)
    except ValueError:
        raise bad_request("invalid_media_id")
    lm = (await db.execute(
        select(ListingMedia).where(
            ListingMedia.listing_id == listing.id,
            ListingMedia.media_id == mid,
            ListingMedia.active.is_(True),
        )
    )).scalar_one_or_none()
    if not lm or not (lm.role or "").startswith("ai_"):
        raise not_found("shot_not_found")
    lm.active = False
    await db.commit()
    return {"ok": True, "media_id": media_id}


@router.post("/listings/{listing_id}/generate-shots")
async def trigger_generate_shots(listing_id: str, artisan: ArtisanProfile = Depends(current_artisan),
                                 db: AsyncSession = Depends(get_db)):
    listing = await _owned(db, listing_id, artisan)
    all_lm = list((await db.execute(
        select(ListingMedia).where(ListingMedia.listing_id == listing.id, ListingMedia.active.is_(True))
    )).scalars())
    for lm in all_lm:
        if (lm.role or "").startswith("ai_"):
            lm.active = False
    job = await enqueue(db, "ai.generate_shots", ref_type="listing", ref_id=str(listing.id),
                        owner_user_id=artisan.user_id)
    await db.commit()
    return {"job_id": str(job.id)}


class ListingPatch(BaseModel):
    title: dict[str, str] | None = None
    description: dict[str, str] | None = None
    attributes: dict | None = None
    tags: list[str] | None = None
    price_inr: float | None = Field(default=None, gt=0, le=10_000_000)
    category_slug: str | None = None
    craft_slug: str | None = None
    returnable: bool | None = None
    shipping: dict | None = None
    photo_media_ids: list[str] | None = Field(default=None, max_length=6)  # full ordered list; first = primary


@router.patch("/listings/{listing_id}")
async def patch_listing(listing_id: str, body: ListingPatch, locale: str = Depends(locale_dep), user=Depends(current_user),
                        artisan: ArtisanProfile = Depends(current_artisan), db: AsyncSession = Depends(get_db)):
    listing = await _owned(db, listing_id, artisan)
    changed: list[str] = []
    if body.title is not None:
        listing.title = {k: v.strip()[:200] for k, v in body.title.items() if k in LOCALES and v and v.strip()}
        changed.append("title")
    if body.description is not None:
        listing.description = {k: v.strip()[:4000] for k, v in body.description.items() if k in LOCALES and v and v.strip()}
        changed.append("description")
    core_changed = False
    if body.attributes is not None:
        clean = attributes.normalize(body.attributes)  # whitelist + shape; the client sends what it has
        old = listing.attributes or {}
        core_changed = any(str(old.get(k) or "").lower() != str(clean.get(k) or "").lower() for k in CORE_ATTRIBUTES)
        listing.attributes = clean
        changed.append("attributes")
    if body.tags is not None:
        listing.tags = [x.strip().lower()[:32] for x in body.tags if x.strip()][:10]
        changed.append("tags")
    if body.price_inr is not None:
        listing.price_inr = Decimal(str(round(body.price_inr, 2)))
        changed.append("price")
    if body.category_slug is not None:
        cat = await category_by_slug(db, body.category_slug)
        if not cat:
            raise bad_request("invalid_category")
        listing.category_id = cat.id
        changed.append("category")
    if body.craft_slug is not None:
        cr = await craft_by_slug(db, body.craft_slug) if body.craft_slug else None
        if body.craft_slug and not cr:
            raise bad_request("invalid_craft")
        core_changed = core_changed or (cr.id if cr else None) != listing.craft_id
        listing.craft_id = cr.id if cr else None
        changed.append("craft")
    if body.returnable is not None:
        listing.returnable = body.returnable
        changed.append("returnable")
    if body.shipping is not None:
        listing.shipping = {k: body.shipping[k] for k in ("weight_g", "dims_cm", "ships_in_days") if k in body.shipping}
        changed.append("shipping")
    photos_changed = False
    if body.photo_media_ids is not None:
        if not body.photo_media_ids:
            raise bad_request("photo_required")
        current = await listing_media(db, listing.id, ("photo", "enhanced_photo"))
        current_ids = [str(m.id) for lm, m in current if lm.role == "photo"]
        if current_ids != body.photo_media_ids:
            new_set = set(body.photo_media_ids)
            photos_changed = set(current_ids) != new_set
            for lm, m in current:
                src = str(lm.source_media_id) if lm.role == "enhanced_photo" else str(m.id)
                if src not in new_set:
                    lm.active = False
            existing = {str(m.id): lm for lm, m in current if lm.role == "photo"}
            enhanced = {str(lm.source_media_id): lm for lm, m in current if lm.role == "enhanced_photo"}
            for i, mid in enumerate(body.photo_media_ids):
                if mid in existing:
                    existing[mid].position, existing[mid].is_primary = i, i == 0
                    if mid in enhanced:
                        enhanced[mid].position, enhanced[mid].is_primary = i, i == 0
                else:
                    m = await owned_media(db, mid, user.id, {"photo"})
                    db.add(ListingMedia(listing_id=listing.id, media_id=m.id, role="photo", position=i, is_primary=i == 0))
            changed.append("photos")
    if not changed:
        return await artisan_view(db, listing, locale)
    if {"attributes", "category", "price"} & set(changed):
        cat = await db.get(Category, listing.category_id) if listing.category_id else None
        listing.missing_fields = attributes.missing_fields(cat.attribute_schema if cat else None, listing.attributes,
                                                           price=listing.price_inr, has_category=cat is not None)
        listing.notes_for_artisan = attributes.notes_for_artisan(price=listing.price_inr, keep=listing.notes_for_artisan)
    await refresh_search(db, listing)
    if listing.status in ("published", "paused"):
        listing.version += 1
        await save_version(db, listing, changed, user.id)
    if photos_changed:
        from app.modules.ai_pipeline.service import enhance_photos

        await db.flush()
        await enhance_photos(db, listing)
        prim = await listing_media(db, listing.id, ("photo",))
        if prim:
            listing.image_embedding = prim[0][1].embedding
        all_lm = list((await db.execute(
            select(ListingMedia).where(ListingMedia.listing_id == listing.id, ListingMedia.active.is_(True))
        )).scalars())
        for lm in all_lm:
            if (lm.role or "").startswith("ai_"):
                lm.active = False
        await enqueue(db, "ai.generate_shots", ref_type="listing", ref_id=str(listing.id), owner_user_id=user.id)
    if listing.status in ("published", "paused") and (photos_changed or core_changed):
        await start_run(db, listing, "edit")
    if "price" in changed or core_changed or "category" in changed:
        await enqueue(db, "pricing.refresh_listing", ref_type="listing", ref_id=str(listing.id))
    await db.commit()
    if listing.status == "published":
        await revalidate_listing(db, listing)
    return await artisan_view(db, listing, locale)


class RegenIn(BaseModel):
    field: str = Field(pattern="^(title|description|tags|attributes|all)$")


@router.post("/listings/{listing_id}/regenerate")
async def regenerate(listing_id: str, body: RegenIn, user=Depends(current_user), artisan: ArtisanProfile = Depends(current_artisan),
                     db: AsyncSession = Depends(get_db)):
    listing = await _owned(db, listing_id, artisan)
    if await _regen_left(db, listing) <= 0:
        raise AppError(429, "regenerate_limit_reached")
    today = utcnow().date().isoformat()
    if listing.regenerate_day != today:
        listing.regenerate_day, listing.regenerate_count = today, 0
    listing.regenerate_count += 1
    job = await enqueue(db, "ai.regenerate", ref_type="listing", ref_id=str(listing.id), owner_user_id=user.id,
                        payload={"field": body.field, "variant": listing.regenerate_count})
    await db.commit()
    return {"job_id": str(job.id)}


class PublishIn(BaseModel):
    quantity: int = Field(ge=1, le=500)
    returnable: bool = True
    category_slug: str | None = None


@router.post("/listings/{listing_id}/publish")
async def publish(listing_id: str, body: PublishIn, locale: str = Depends(locale_dep), user=Depends(current_user),
                  artisan: ArtisanProfile = Depends(current_artisan), db: AsyncSession = Depends(get_db)):
    from app.modules.artisans.service import get_passport
    from app.modules.notifications.service import notify
    from app.modules.reviews.models import Follow

    listing = await _owned(db, listing_id, artisan)
    if listing.status not in ("draft",):
        raise AppError(409, "not_a_draft")
    passport = await get_passport(db, artisan.id)
    if passport and passport.state == "suspended":
        raise AppError(403, "passport_suspended")
    if body.category_slug:
        cat = await category_by_slug(db, body.category_slug)
        if not cat:
            raise bad_request("invalid_category")
        listing.category_id = cat.id
    missing = []
    if not any((listing.title or {}).values()):
        missing.append("title")
    if listing.price_inr is None:
        missing.append("price")
    if listing.category_id is None:
        missing.append("category")
    if not await listing_media(db, listing.id, ("photo",)):
        missing.append("photo")
    if missing:
        raise bad_request("listing_incomplete", missing=missing)
    listing.returnable = body.returnable
    listing.status = "published"
    listing.published_at = utcnow()
    await refresh_search(db, listing)
    await save_version(db, listing, ["publish"], user.id)
    units = await create_karu_ids(db, listing, body.quantity, user.id)
    run = await start_run(db, listing, "publish")
    title = (listing.title or {}).get(listing.source_lang) or next(iter(listing.title.values()))
    await notify(db, user.id, "listing_published", {"title": title, "count": len(units)}, link=f"/sell/products/{listing.id}")
    followers = (await db.execute(select(Follow.user_id).where(Follow.artisan_id == artisan.id))).scalars().all()
    for fid in followers:
        await notify(db, fid, "maker_new_product", {"maker": artisan.public_name, "title": title},
                     link=f"/p/{listing.short_code}", artisan_side=False)
    await db.commit()
    await revalidate_listing(db, listing)
    return {"listing_id": str(listing.id), "short_code": listing.short_code, "karu_ids": [u.code for u in units],
            "verification_status": listing.verification_status, "verification_run_id": str(run.id),
            "share_url": short_url(listing)}


@router.post("/listings/{listing_id}/pause")
async def pause(listing_id: str, artisan: ArtisanProfile = Depends(current_artisan), db: AsyncSession = Depends(get_db)):
    listing = await _owned(db, listing_id, artisan)
    if listing.status != "published":
        raise AppError(409, "not_published")
    listing.status, listing.paused_at = "paused", utcnow()
    await db.commit()
    await revalidate_listing(db, listing)
    return {"status": listing.status}


@router.post("/listings/{listing_id}/resume")
async def resume(listing_id: str, artisan: ArtisanProfile = Depends(current_artisan), db: AsyncSession = Depends(get_db)):
    listing = await _owned(db, listing_id, artisan)
    if listing.status != "paused":
        raise AppError(409, "not_paused")
    listing.status, listing.paused_at = "published", None
    await db.commit()
    await revalidate_listing(db, listing)
    return {"status": listing.status}


@router.delete("/listings/{listing_id}")
async def delete_listing(listing_id: str, artisan: ArtisanProfile = Depends(current_artisan), db: AsyncSession = Depends(get_db)):
    """Soft delete: hidden everywhere; sold Karu IDs stay valid forever (Part 1 §4.1)."""
    listing = await _owned(db, listing_id, artisan)
    listing.status, listing.deleted_at = "deleted", utcnow()
    units = (await db.execute(select(KaruId).where(KaruId.listing_id == listing.id, KaruId.status == "available"))).scalars().all()
    for u in units:
        u.status = "retired"
        db.add(KaruIdEvent(karu_id=u.id, event="retired", data={"reason": "listing_deleted"}))
    await sync_quantity(db, listing)
    await db.commit()
    await revalidate_listing(db, listing)
    return {"status": "deleted"}


class StockIn(BaseModel):
    add: int = Field(ge=1, le=500)


@router.post("/listings/{listing_id}/stock")
async def add_stock(listing_id: str, body: StockIn, user=Depends(current_user), artisan: ArtisanProfile = Depends(current_artisan),
                    db: AsyncSession = Depends(get_db)):
    listing = await _owned(db, listing_id, artisan)
    if listing.status not in ("published", "paused"):
        raise AppError(409, "not_published")
    units = await create_karu_ids(db, listing, body.add, user.id)
    await db.commit()
    await revalidate_listing(db, listing)
    return {"created": [u.code for u in units], "quantity_available": listing.quantity_available}


@router.get("/listings/{listing_id}/karu-ids")
async def karu_ids(listing_id: str, artisan: ArtisanProfile = Depends(current_artisan), db: AsyncSession = Depends(get_db)):
    listing = await _owned(db, listing_id, artisan)
    rows = (await db.execute(select(KaruId).where(KaruId.listing_id == listing.id).order_by(KaruId.created_at))).scalars().all()
    return {"items": [{"code": u.code, "status": u.status, "verified": u.verification_run_id is not None,
                       "url": unit_url(u.code), "sold_at": u.sold_at.isoformat() if u.sold_at else None,
                       "created_at": u.created_at.isoformat()} for u in rows]}


@router.get("/listings/{listing_id}/price-advice")
async def price_advice(listing_id: str, locale: str = Depends(locale_dep), artisan: ArtisanProfile = Depends(current_artisan),
                       db: AsyncSession = Depends(get_db)):
    listing = await _owned(db, listing_id, artisan)
    view = await advice_view(db, listing, locale)
    await db.commit()
    return view


class AcceptIn(BaseModel):
    price_inr: float = Field(gt=0)


@router.post("/listings/{listing_id}/price-advice/accept")
async def accept_price(listing_id: str, body: AcceptIn, locale: str = Depends(locale_dep), user=Depends(current_user),
                       artisan: ArtisanProfile = Depends(current_artisan), db: AsyncSession = Depends(get_db)):
    """The artisan taps 'Use ₹2,800' — Karu never changes a price on its own."""
    from app.modules.pricing.models import ListingPriceAdvice
    from app.modules.pricing.service import compute_advice

    listing = await _owned(db, listing_id, artisan)
    advice = (await db.execute(select(ListingPriceAdvice).where(ListingPriceAdvice.listing_id == listing.id)
                               .order_by(desc(ListingPriceAdvice.created_at)).limit(1))).scalar_one_or_none()
    if advice:
        advice.accepted = True
    listing.price_inr = Decimal(str(round(body.price_inr, 2)))
    if listing.status in ("published", "paused"):
        listing.version += 1
        await save_version(db, listing, ["price"], user.id)
    from app.modules.pricing.models import PriceBenchmark

    bm = await db.get(PriceBenchmark, listing.current_benchmark_id) if listing.current_benchmark_id else None
    new = await compute_advice(db, listing, bm)
    new.accepted = True
    await db.commit()
    return await advice_view(db, listing, locale)


class VideoIn(BaseModel):
    media_id: str


@router.post("/listings/{listing_id}/making-video")
async def attach_video(listing_id: str, body: VideoIn, user=Depends(current_user), artisan: ArtisanProfile = Depends(current_artisan),
                       db: AsyncSession = Depends(get_db)):
    listing = await _owned(db, listing_id, artisan)
    m = await owned_media(db, body.media_id, user.id, {"video"})
    for lm, _ in await listing_media(db, listing.id, ("making_video",)):
        lm.active = False
    db.add(ListingMedia(listing_id=listing.id, media_id=m.id, role="making_video"))
    run_id = None
    if listing.status in ("published", "paused"):
        run = await start_run(db, listing, "video")
        run_id = str(run.id)
    await db.commit()
    return {"ok": True, "verification_status": listing.verification_status, "verification_run_id": run_id}


@router.post("/listings/{listing_id}/verify")
async def retry_verification(listing_id: str, artisan: ArtisanProfile = Depends(current_artisan), db: AsyncSession = Depends(get_db)):
    listing = await _owned(db, listing_id, artisan)
    if listing.status not in ("published", "paused"):
        raise AppError(409, "not_published")
    if listing.verification_status == "checking":
        raise AppError(409, "already_checking")
    run = await start_run(db, listing, "retry")
    await db.commit()
    return {"verification_status": "checking", "verification_run_id": str(run.id)}


@router.get("/listings/{listing_id}/verification")
async def verification_view(listing_id: str, locale: str = Depends(locale_dep), artisan: ArtisanProfile = Depends(current_artisan),
                            db: AsyncSession = Depends(get_db)):
    """Artisans see verdict + per-layer status + tips, never numbers (Part 1 §3.3 rule 5)."""
    listing = await _owned(db, listing_id, artisan)
    run = await latest_run(db, listing)
    vids = await listing_media(db, listing.id, ("making_video",))
    out = {"status": listing.verification_status, "has_video": bool(vids), "run": None}
    if run:
        out["run"] = {
            "id": str(run.id), "status": run.status, "verdict": run.verdict,
            "layers": run.layer_status or {}, "hard_fail": run.hard_fail,
            "tips": [{"key": k, "text": t(k, locale)} for k in (run.artisan_tips or [])],
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "triggered_by": run.triggered_by,
        }
    return out


class ShareIn(BaseModel):
    format: str = Field(default="4x5", pattern="^(4x5|9x16|og|clean)$")
    locale: str | None = None


@router.post("/listings/{listing_id}/share-image")
async def make_share_image(listing_id: str, body: ShareIn, locale: str = Depends(locale_dep),
                           artisan: ArtisanProfile = Depends(current_artisan), db: AsyncSession = Depends(get_db)):
    listing = await _owned(db, listing_id, artisan)
    if listing.status not in ("published", "paused"):
        raise AppError(409, "not_published")
    loc = body.locale if body.locale in LOCALES else locale
    res = await share_image(db, listing, body.format if body.format != "clean" else "4x5", loc, clean=body.format == "clean")
    listing.share_count += 1
    await db.commit()
    return res


@router.get("/listings/{listing_id}/tags.pdf")
async def tags_pdf(listing_id: str, locale: str = Depends(locale_dep), artisan: ArtisanProfile = Depends(current_artisan),
                   db: AsyncSession = Depends(get_db)):
    listing = await _owned(db, listing_id, artisan)
    pdf = await tag_sheet(db, listing, locale)
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="karu-tags-{listing.short_code}.pdf"'})


class SyndicateIn(BaseModel):
    portal: str = Field(pattern="^(ondc|indiamart|coop)$")


@router.post("/listings/{listing_id}/syndicate")
async def syndicate(listing_id: str, body: SyndicateIn, user=Depends(current_user), artisan: ArtisanProfile = Depends(current_artisan),
                    db: AsyncSession = Depends(get_db)):
    """[DEMO] TinyFish Agent publishes to a team-owned demo seller account (flag `syndication.demo`)."""
    from app.modules.syndication import service as _syn  # noqa: F401
    from app.modules.syndication.models import SyndicationJob

    if not await flag(db, "syndication.demo"):
        raise AppError(403, "feature_disabled")
    listing = await _owned(db, listing_id, artisan)
    if listing.status != "published":
        raise AppError(409, "not_published")
    sj = SyndicationJob(listing_id=listing.id, portal=body.portal, status="queued", steps=[])
    db.add(sj)
    await db.flush()
    job = await enqueue(db, "agents.syndicate", ref_type="syndication", ref_id=str(sj.id), owner_user_id=user.id,
                        payload={"syndication_id": str(sj.id)})
    sj.job_id = job.id
    await db.commit()
    return {"syndication_id": str(sj.id), "job_id": str(job.id)}
