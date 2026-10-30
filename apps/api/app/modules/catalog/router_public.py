from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import ratelimit
from app.core.db import get_db, utcnow
from app.core.deps import ip_hash, locale_dep, optional_user
from app.core.errors import AppError
from app.core.i18n import format_inr, pick_lang
from app.core.ids import is_karu_id, is_short_code, normalise_code
from app.core.jobs import enqueue
from app.modules.artisans.models import ArtisanProfile, Passport
from app.modules.artisans.service import public_maker
from app.modules.catalog.models import Craft, Listing
from app.modules.catalog.service import all_categories, cards, search, similar_listings
from app.modules.karu_ids.models import KaruId, ScanAggregate
from app.modules.karu_ids.service import product_public, public_karu_id

router = APIRouter(tags=["catalog"])


def _public_listing_q():
    return (select(Listing).join(Passport, Passport.artisan_id == Listing.artisan_id)
            .where(Listing.status == "published", Listing.hidden_by_staff.is_(False), Passport.state != "suspended"))


async def impact_numbers(db: AsyncSession) -> dict:
    from app.modules.orders.models import OrderItem
    from app.modules.payments.models import Transfer

    artisans = (await db.execute(select(func.count()).select_from(ArtisanProfile).where(
        ArtisanProfile.onboarding_completed_at.is_not(None)))).scalar_one()
    verified = (await db.execute(select(func.count()).select_from(KaruId).where(KaruId.verification_run_id.is_not(None)))).scalar_one()
    paid = (await db.execute(select(func.coalesce(func.sum(Transfer.amount), 0)).where(
        Transfer.status.in_(["released", "settled"])))).scalar_one()
    sold_total = (await db.execute(select(func.coalesce(func.sum(OrderItem.unit_price), 0)).where(
        OrderItem.fulfilment_status.in_(["to_pack", "shipped", "delivered"])))).scalar_one()
    districts = (await db.execute(select(func.count(func.distinct(ArtisanProfile.district))).where(
        ArtisanProfile.district.is_not(None)))).scalar_one()
    states = (await db.execute(select(func.count(func.distinct(ArtisanProfile.state))).where(
        ArtisanProfile.state.is_not(None)))).scalar_one()
    return {"artisans": artisans, "pieces_verified": verified, "paid_to_artisans_inr": float(paid),
            "paid_to_artisans": format_inr(paid), "sales_inr": float(sold_total), "clusters": districts, "states": states}


@router.get("/catalog/home")
async def home(locale: str = Depends(locale_dep), user=Depends(optional_user), db: AsyncSession = Depends(get_db)):
    viewer = user.id if user else None
    cats = await all_categories(db)
    verified = list((await db.execute(_public_listing_q().where(Listing.verification_status == "verified")
                                      .order_by(desc(Listing.published_at)).limit(12))).scalars())
    newest = list((await db.execute(_public_listing_q().order_by(desc(Listing.published_at)).limit(12))).scalars())
    crafts = list((await db.execute(select(Craft).order_by(Craft.slug))).scalars())
    rails = []
    for c in crafts:
        items = list((await db.execute(_public_listing_q().where(Listing.craft_id == c.id)
                                       .order_by(desc(Listing.verification_status == "verified"), desc(Listing.published_at))
                                       .limit(10))).scalars())
        if items:
            rails.append({"craft": {"slug": c.slug, "name": pick_lang(c.name, locale)[0], "gi_tag": c.gi_tag,
                                    "regions": c.regions}, "items": await cards(db, items, locale, viewer)})
    makers_rows = list((await db.execute(
        select(ArtisanProfile).join(Passport, Passport.artisan_id == ArtisanProfile.id)
        .where(Passport.state != "suspended", ArtisanProfile.onboarding_completed_at.is_not(None))
        .order_by(desc(Passport.state == "verified"), desc(ArtisanProfile.created_at)).limit(8))).scalars())
    makers = [await public_maker(db, m, locale) for m in makers_rows]
    counts = dict((await db.execute(select(Listing.category_id, func.count()).where(Listing.status == "published")
                                    .group_by(Listing.category_id))).all())
    return {
        "categories": [{"slug": c.slug, "name": pick_lang(c.name, locale)[0], "icon": c.icon, "count": counts.get(c.id, 0)}
                       for c in cats],
        "verified_picks": await cards(db, verified, locale, viewer),
        "new_arrivals": await cards(db, newest, locale, viewer),
        "craft_rails": rails,
        "makers": makers,
        "impact": await impact_numbers(db),
    }


@router.get("/catalog/categories")
async def categories(locale: str = Depends(locale_dep), db: AsyncSession = Depends(get_db)):
    cats = await all_categories(db)
    return {"items": [{"slug": c.slug, "name": pick_lang(c.name, locale)[0], "names": c.name, "icon": c.icon,
                       "attribute_schema": c.attribute_schema} for c in cats]}


@router.get("/catalog/crafts")
async def crafts(locale: str = Depends(locale_dep), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Craft).order_by(Craft.slug))).scalars().all()
    return {"items": [{"slug": c.slug, "name": pick_lang(c.name, locale)[0], "names": c.name, "gi_tag": c.gi_tag,
                       "regions": c.regions, "category_slug": c.category_slug} for c in rows]}


@router.get("/catalog/crafts/{slug}")
async def craft_page(slug: str, locale: str = Depends(locale_dep), user=Depends(optional_user), db: AsyncSession = Depends(get_db)):
    c = (await db.execute(select(Craft).where(Craft.slug == slug))).scalar_one_or_none()
    if c is None:
        raise AppError(404, "craft_not_found")
    items = list((await db.execute(_public_listing_q().where(Listing.craft_id == c.id)
                                   .order_by(desc(Listing.published_at)).limit(48))).scalars())
    maker_ids = list(dict.fromkeys(li.artisan_id for li in items))[:12]
    makers = [await public_maker(db, await db.get(ArtisanProfile, mid), locale) for mid in maker_ids]
    desc_text, desc_lang = pick_lang(c.description, locale)
    return {"slug": c.slug, "name": pick_lang(c.name, locale)[0], "description": desc_text, "description_lang": desc_lang,
            "gi_tag": c.gi_tag, "regions": c.regions, "category_slug": c.category_slug, "makers": makers,
            "items": await cards(db, items, locale, user.id if user else None)}


@router.get("/catalog/search")
async def search_endpoint(
    request: Request,
    q: str | None = Query(None, max_length=120),
    category: str | None = None, craft: str | None = None, state: str | None = None, material: str | None = None,
    verified: bool = False, returnable: bool | None = None, in_stock: bool | None = None,
    min_price: float | None = Query(None, ge=0), max_price: float | None = Query(None, ge=0),
    min_rating: float | None = Query(None, ge=0, le=5), maker: str | None = None,
    sort: str = Query("relevance", pattern="^(relevance|new|price_asc|price_desc|rating)$"),
    cursor: int = Query(0, ge=0), limit: int = Query(24, ge=1, le=60),
    locale: str = Depends(locale_dep), user=Depends(optional_user), db: AsyncSession = Depends(get_db),
):
    await ratelimit.enforce(f"search:{ip_hash(request)}", 120, 60)
    page, total, facets = await search(db, q=q, category=category, craft=craft, state=state, material=material,
                                       verified_only=verified, returnable=returnable, in_stock=in_stock, min_price=min_price,
                                       max_price=max_price, min_rating=min_rating, maker_handle=maker, sort=sort,
                                       offset=cursor, limit=limit)
    nxt = cursor + limit if cursor + limit < total else None
    return {"items": await cards(db, page, locale, user.id if user else None), "total": total, "next_cursor": nxt,
            "facets": facets}


@router.get("/catalog/suggest")
async def suggest(q: str = Query(..., min_length=1, max_length=60), locale: str = Depends(locale_dep),
                  db: AsyncSession = Depends(get_db)):
    """Search-as-you-type: crafts, categories and product titles, transliteration-aware."""
    from app.core.translit import phonetic_key
    from app.modules.catalog.service import relevance

    keys = phonetic_key(q).split()
    out: list[dict] = []
    for c in (await db.execute(select(Craft))).scalars():
        if relevance(keys, "A:" + phonetic_key(" ".join(c.name.values()))):
            out.append({"type": "craft", "slug": c.slug, "label": pick_lang(c.name, locale)[0]})
    for c in await all_categories(db):
        if relevance(keys, "A:" + phonetic_key(" ".join(c.name.values()) + " " + c.slug.replace("-", " "))):
            out.append({"type": "category", "slug": c.slug, "label": pick_lang(c.name, locale)[0]})
    page, _, _ = await search(db, q=q, limit=6)
    for li in page:
        out.append({"type": "product", "code": li.short_code, "label": pick_lang(li.title, locale)[0]})
    return {"items": out[:10]}


async def _public_listing(db: AsyncSession, code: str) -> Listing:
    code = normalise_code(code)
    listing = (await db.execute(select(Listing).where(Listing.short_code == code))).scalar_one_or_none()
    if listing is None or listing.status in ("draft", "processing"):
        raise AppError(404, "product_not_found")
    return listing


@router.get("/catalog/products/{code}")
async def product(code: str, locale: str = Depends(locale_dep), user=Depends(optional_user), db: AsyncSession = Depends(get_db)):
    listing = await _public_listing(db, code)
    passport = (await db.execute(select(Passport).where(Passport.artisan_id == listing.artisan_id))).scalar_one_or_none()
    hidden = listing.status == "deleted" or listing.hidden_by_staff or (passport and passport.state == "suspended")
    if hidden and not (user and user.id == (await db.get(ArtisanProfile, listing.artisan_id)).user_id):
        raise AppError(410 if listing.status == "deleted" else 404, "product_unavailable")
    data = await product_public(db, listing, locale, user.id if user else None)
    listing.views_count += 1
    listing.last_viewed_at = utcnow()
    hour = utcnow().replace(minute=0, second=0, microsecond=0)
    agg = (await db.execute(select(ScanAggregate).where(ScanAggregate.target_type == "view", ScanAggregate.target_code == listing.short_code,
                                                        ScanAggregate.hour == hour))).scalar_one_or_none()
    if agg is None:
        db.add(ScanAggregate(target_type="view", target_code=listing.short_code, hour=hour, count=1))
    else:
        agg.count += 1
    if locale not in (listing.description or {}) and listing.description:
        from app.modules.jobs.models import Job

        pending = (await db.execute(select(Job.id).where(Job.type == "ai.translate", Job.ref_id == str(listing.id),
                                                         Job.status.in_(["queued", "running"])))).first()
        if not pending:
            await enqueue(db, "ai.translate", ref_type="listing", ref_id=str(listing.id), payload={"locale": locale})
    await db.commit()
    return data


@router.get("/catalog/cards")
async def cards_by_id(ids: str = Query(..., max_length=2000), locale: str = Depends(locale_dep), user=Depends(optional_user),
                      db: AsyncSession = Depends(get_db)):
    """Product cards for given listing ids (buy-now checkout, wishlists synced from devices)."""
    wanted = []
    for raw in ids.split(",")[:50]:
        try:
            wanted.append(uuid.UUID(raw.strip()))
        except ValueError:
            continue
    rows = list((await db.execute(_public_listing_q().where(Listing.id.in_(wanted)))).scalars()) if wanted else []
    return {"items": await cards(db, rows, locale, user.id if user else None)}


@router.get("/catalog/products/{code}/og.jpg")
async def og_image(code: str, locale: str = Depends(locale_dep), db: AsyncSession = Depends(get_db)):
    """OpenGraph image (1200×630: photo + Karu badge) for WhatsApp/Instagram link previews."""
    from fastapi.responses import RedirectResponse

    from app.modules.karu_ids.service import share_image

    listing = await _public_listing(db, code)
    if listing.status != "published" or listing.hidden_by_staff:
        raise AppError(404, "product_not_found")
    res = await share_image(db, listing, "og", locale)
    return RedirectResponse(res["image_url"], status_code=302, headers={"Cache-Control": "public, max-age=3600"})


@router.get("/catalog/products/{code}/similar")
async def similar(code: str, locale: str = Depends(locale_dep), user=Depends(optional_user), db: AsyncSession = Depends(get_db)):
    listing = await _public_listing(db, code)
    return {"items": await cards(db, await similar_listings(db, listing), locale, user.id if user else None)}


@router.get("/catalog/products/{code}/reviews")
async def product_reviews(code: str, cursor: int = 0, limit: int = Query(10, le=50), db: AsyncSession = Depends(get_db)):
    from app.modules.auth.models import User
    from app.modules.reviews.models import Review

    listing = await _public_listing(db, code)
    rows = (await db.execute(select(Review, User).join(User, User.id == Review.buyer_user_id)
                             .where(Review.listing_id == listing.id, Review.status == "published")
                             .order_by(desc(Review.created_at)).offset(cursor).limit(limit))).all()
    from app.modules.media.models import Media
    from app.modules.media.service import public_url

    items = []
    for r, u in rows:
        photos = []
        for mid in r.photos or []:
            m = await db.get(Media, uuid.UUID(mid))
            if m:
                photos.append(public_url(m, "400_4x5.jpg"))
        items.append({"id": str(r.id), "rating": r.rating, "text": r.text, "photos": photos,
                      "buyer": (u.display_name or "Karu buyer").split(" ")[0], "created_at": r.created_at.isoformat()})
    return {"items": items}


@router.get("/karu-ids/{code}")
async def karu_id(code: str, locale: str = Depends(locale_dep), user=Depends(optional_user), db: AsyncSession = Depends(get_db)):
    code = normalise_code(code)
    if not is_karu_id(code) and not is_short_code(code):
        raise AppError(404, "karu_id_not_found")
    data = await public_karu_id(db, code, locale, user.id if user else None)
    if data is None:
        raise AppError(404, "karu_id_not_found")
    return data


@router.get("/karu-ids/{code}/qr.png")
async def karu_id_qr_png(code: str, db: AsyncSession = Depends(get_db)):
    """Crisp scannable QR code PNG for the Karu ID certificate."""
    code = normalise_code(code)
    if not is_karu_id(code) and not is_short_code(code):
        raise AppError(404, "karu_id_not_found")
    data = await public_karu_id(db, code, "en", None)
    if not data:
        raise AppError(404, "karu_id_not_found")
    from fastapi.responses import Response

    from app.core.config import get_settings
    from app.core.imaging import encode, make_qr

    target_url = f"{get_settings().public_base_url}/k/{data['code']}"
    qr_img = make_qr(target_url, 320)
    png_bytes = encode(qr_img, "PNG", 95)
    return Response(content=png_bytes, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})


@router.get("/makers")
async def list_makers(
    craft: str | None = None,
    state: str | None = None,
    cursor: int = Query(0, ge=0),
    limit: int = Query(24, ge=1, le=60),
    locale: str = Depends(locale_dep),
    db: AsyncSession = Depends(get_db),
):
    """List public makers with optional craft and state filtering (section 10.2)."""
    query = select(ArtisanProfile).where(ArtisanProfile.handle.is_not(None))
    if state:
        query = query.where(func.lower(ArtisanProfile.state) == state.lower())
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    profiles = (await db.execute(query.order_by(ArtisanProfile.created_at.desc()).offset(cursor).limit(limit))).scalars().all()
    out = []
    for p in profiles:
        m_data = await public_maker(db, p, locale)
        if craft:
            if not any(craft.lower() in c.lower() for c in m_data.get("crafts", [])):
                continue
        out.append(m_data)
    nxt = cursor + limit if cursor + limit < total else None
    return {"items": out, "total": total, "next_cursor": nxt}


@router.get("/makers/{handle}")
async def maker(handle: str, locale: str = Depends(locale_dep), user=Depends(optional_user), db: AsyncSession = Depends(get_db)):
    from app.modules.reviews.models import Follow

    p = (await db.execute(select(ArtisanProfile).where(ArtisanProfile.handle == handle.lower()))).scalar_one_or_none()
    if p is None:
        raise AppError(404, "maker_not_found")
    passport = (await db.execute(select(Passport).where(Passport.artisan_id == p.id))).scalar_one_or_none()
    if passport and passport.state == "suspended":
        return {"under_review": True, "handle": p.handle}
    data = await public_maker(db, p, locale)
    if user:
        data["following"] = (await db.execute(select(Follow.id).where(Follow.user_id == user.id, Follow.artisan_id == p.id))).first() is not None
    return data


@router.get("/makers/{handle}/products")
async def maker_products(handle: str, locale: str = Depends(locale_dep), user=Depends(optional_user),
                         db: AsyncSession = Depends(get_db)):
    page, total, _ = await search(db, q=None, maker_handle=handle.lower(), sort="new", limit=60)
    return {"items": await cards(db, page, locale, user.id if user else None), "total": total}


@router.get("/makers/{handle}/reviews")
async def maker_reviews(handle: str, db: AsyncSession = Depends(get_db)):
    from app.modules.auth.models import User
    from app.modules.reviews.models import Review

    p = (await db.execute(select(ArtisanProfile).where(ArtisanProfile.handle == handle.lower()))).scalar_one_or_none()
    if p is None:
        raise AppError(404, "maker_not_found")
    rows = (await db.execute(select(Review, User, Listing).join(User, User.id == Review.buyer_user_id)
                             .join(Listing, Listing.id == Review.listing_id)
                             .where(Review.artisan_id == p.id, Review.status == "published")
                             .order_by(desc(Review.created_at)).limit(30))).all()
    return {"items": [{"rating": r.rating, "text": r.text, "buyer": (u.display_name or "Karu buyer").split(" ")[0],
                       "product": pick_lang(li.title, "en")[0], "code": li.short_code, "created_at": r.created_at.isoformat()}
                      for r, u, li in rows]}


class ScanIn(BaseModel):
    type: str = Field(pattern="^(karu_id|listing)$")
    code: str = Field(max_length=16)


@router.post("/scans")
async def scan(body: ScanIn, request: Request, db: AsyncSession = Depends(get_db)):
    """Anonymous scan beacon, aggregated hourly, no PII (Part 2 §9.4)."""
    if not await ratelimit.hit(f"scan:{ip_hash(request)}", 60, 60):
        return {"ok": True}
    hour = utcnow().replace(minute=0, second=0, microsecond=0)
    code = normalise_code(body.code)
    row = (await db.execute(select(ScanAggregate).where(ScanAggregate.target_type == body.type, ScanAggregate.target_code == code,
                                                        ScanAggregate.hour == hour))).scalar_one_or_none()
    if row is None:
        db.add(ScanAggregate(target_type=body.type, target_code=code, hour=hour, count=1))
    else:
        row.count += 1
    await db.commit()
    return {"ok": True}


@router.get("/impact")
async def impact(db: AsyncSession = Depends(get_db)):
    return await impact_numbers(db)


@router.get("/config/public")
async def public_config(db: AsyncSession = Depends(get_db)):
    """Capabilities the web app adapts to (which providers are live, feature flags, limits)."""
    from app.core.appconfig import get_config
    from app.core.config import get_settings
    from app.providers.llm import get_llm
    from app.providers.messaging import messaging_is_fake
    from app.providers.payments import get_payments
    from app.providers.stt import get_stt
    from app.providers.webintel import get_webintel

    s = get_settings()
    return {
        "providers": {"llm": get_llm().name, "stt": get_stt().name, "web": get_webintel().name,
                      "payments": get_payments().name, "messaging": "fake" if messaging_is_fake() else "live"},
        "razorpay_key_id": get_payments().key_id if get_payments().name == "razorpay" else None,
        "google_client_id": s.google_client_id or None,
        "flags": await get_config(db, "flags"),
        "limits": await get_config(db, "limits.v1"),
        "commerce": await get_config(db, "commerce.v1"),
        "env": s.env,
    }
