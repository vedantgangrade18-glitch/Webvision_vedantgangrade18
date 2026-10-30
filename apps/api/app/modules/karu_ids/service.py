from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import imaging
from app.core.config import get_settings
from app.core.i18n import format_date, format_inr, pick_lang, t
from app.core.storage import get_storage
from app.modules.artisans.models import ArtisanProfile, Passport
from app.modules.artisans.service import place_of, public_maker
from app.modules.catalog import attributes
from app.modules.catalog.models import Craft, Listing
from app.modules.catalog.service import gallery, listing_media, primary_images, proof_projection
from app.modules.karu_ids.models import KaruId, KaruIdEvent


def short_url(listing: Listing) -> str:
    return f"{get_settings().public_base_url}/p/{listing.short_code}"


def unit_url(code: str) -> str:
    return f"{get_settings().public_base_url}/k/{code}"


async def public_karu_id(db: AsyncSession, code: str, locale: str, viewer_id: uuid.UUID | None) -> dict | None:
    unit = (await db.execute(select(KaruId).where(KaruId.code == code))).scalar_one_or_none()
    if unit is None:
        listing_match = (await db.execute(select(Listing).where(Listing.short_code == code))).scalar_one_or_none()
        if listing_match:
            unit = (await db.execute(select(KaruId).where(KaruId.listing_id == listing_match.id).order_by(KaruId.created_at))).scalars().first()
            if unit is None:
                from app.core.ids import new_karu_id, uuid7
                unit = KaruId(
                    id=uuid7(),
                    code=new_karu_id(),
                    listing_id=listing_match.id,
                    artisan_id=listing_match.artisan_id,
                    status="available",
                )
                db.add(unit)
                await db.commit()
                await db.refresh(unit)
    if unit is None:
        return None
    listing = await db.get(Listing, unit.listing_id)
    profile = await db.get(ArtisanProfile, unit.artisan_id)
    passport = (await db.execute(select(Passport).where(Passport.artisan_id == profile.id))).scalar_one_or_none()
    craft = await db.get(Craft, listing.craft_id) if listing.craft_id else None
    suspended = passport is not None and passport.state == "suspended"

    if listing.verification_status == "revoked":
        verdict = "revoked"
    elif unit.verification_run_id and listing.verification_status in ("verified", "checking"):
        verdict = "verified"
    elif listing.verification_status == "checking":
        verdict = "checking"
    else:
        verdict = "not_verified"

    title, title_lang = pick_lang(listing.title, locale)
    images = await primary_images(db, [listing.id])
    events = (await db.execute(select(KaruIdEvent).where(KaruIdEvent.karu_id == unit.id).order_by(KaruIdEvent.at))).scalars().all()
    journey = [{"event": "made", "date": format_date(unit.created_at, locale)}]
    if listing.published_at:
        journey.append({"event": "listed", "date": format_date(listing.published_at, locale)})
    if unit.sold_at:
        journey.append({"event": "sold", "date": format_date(unit.sold_at, locale), "city": unit.sold_city})
    for e in events:
        if e.event == "delivered":
            journey.append({"event": "delivered", "date": format_date(e.at, locale)})
        if e.event == "returned":
            journey.append({"event": "returned", "date": format_date(e.at, locale)})
    owned_by_viewer = viewer_id is not None and unit.current_owner_user_id == viewer_id
    if unit.owned_since and unit.status == "sold":
        journey.append({"event": "owned", "date": format_date(unit.owned_since, locale), "by_viewer": owned_by_viewer})

    proof = await proof_projection(db, listing, locale)
    if verdict != "verified":
        proof["checks"] = proof["checks"] if verdict == "checking" else []
        proof["making_video"] = None

    market = None
    if verdict == "verified" and listing.current_benchmark_id:
        from app.modules.pricing.models import PriceBenchmark

        bm = await db.get(PriceBenchmark, listing.current_benchmark_id)
        if bm and bm.handmade_p25 is not None:
            market = {"low": format_inr(bm.handmade_p25), "high": format_inr(bm.handmade_p75)}

    maker = {"under_review": True} if suspended else await public_maker(db, profile, locale, include_stats=False)
    return {
        "code": unit.code,
        "status": unit.status,
        "verdict": verdict,
        "verified_label": t("badge.verified" if verdict == "verified" else "badge.not_verified", locale),
        "piece": {
            "title": title, "title_lang": title_lang, "code": listing.short_code,
            "craft": (craft.name or {}).get(locale) or (craft.name or {}).get("en") if craft else None,
            "craft_slug": craft.slug if craft else None,
            "region": place_of(profile),
            "image": images.get(listing.id),
            "listing_status": listing.status,
            "available": listing.status == "published" and listing.quantity_available > 0 and not suspended,
            "price_inr": float(listing.price_inr) if listing.price_inr is not None else None,
        },
        "maker": maker,
        "proof": proof,
        "journey": journey,
        "sold": unit.status in ("sold", "returned") and unit.sold_at is not None,
        "sold_on": format_date(unit.sold_at, locale) if unit.sold_at else None,
        "owned_by_viewer": owned_by_viewer,
        "market_context": market,
    }


async def share_image(db: AsyncSession, listing: Listing, fmt: str, locale: str, *, clean: bool = False) -> dict:
    """Cached by (listing version, verification status, format, locale) — Part 2 §9.3."""
    st = get_storage()
    profile = await db.get(ArtisanProfile, listing.artisan_id)
    status = listing.verification_status
    key = f"share/{listing.id}/v{listing.version}-{status}-{'clean' if clean else fmt}-{locale}.jpg"
    try:
        await st.get_public(key)
        cached = True
    except Exception:  # noqa: BLE001
        cached = False
    title, _ = pick_lang(listing.title, locale)
    url = short_url(listing)
    if not cached:
        rows = await listing_media(db, listing.id, ("enhanced_photo", "photo"))
        rows.sort(key=lambda r: (r[0].role != "enhanced_photo", not r[0].is_primary, r[0].position))
        photo = None
        if rows:
            data = await st.get_private(rows[0][1].storage_key)
            photo = await asyncio.to_thread(imaging.load_image, data)
        if clean:
            # Clean image for Amazon/Flipkart: enhanced photo only, no QR, logo or text (Part 1 §4.5).
            img = imaging.crop_to_ratio(photo, 1, 1).resize((1600, 1600)) if photo else None
            blob = imaging.encode(img, "JPEG", 92) if img else b""
        else:
            verified = status == "verified"
            blob = await asyncio.to_thread(
                imaging.render_share_image, photo, fmt=fmt, title=title, maker=f"{profile.public_name} · {place_of(profile)}",
                verdict_label=t("badge.verified" if verified else "badge.not_verified", locale), verified=verified,
                short_url=url.split("://")[-1], qr_url=None if fmt == "og" else url,
            )
        await st.put_public(key, blob, "image/jpeg")
    caption = t("share.caption", locale, title=title, maker=profile.public_name, place=place_of(profile), url=url)
    if locale != "en":
        caption += "\n\n" + t("share.caption", "en", title=(listing.title or {}).get("en") or title,
                              maker=profile.public_name, place=place_of(profile), url=url)
    return {"image_url": st.public_url(key), "caption": caption, "url": url, "format": "clean" if clean else fmt,
            "whatsapp_url": f"https://wa.me/?text={_urlencode(caption)}"}


def _urlencode(text: str) -> str:
    from urllib.parse import quote

    return quote(text, safe="")


async def tag_sheet(db: AsyncSession, listing: Listing, locale: str) -> bytes:
    profile = await db.get(ArtisanProfile, listing.artisan_id)
    units = (await db.execute(select(KaruId).where(KaruId.listing_id == listing.id, KaruId.status.in_(["available", "reserved", "sold"]))
                              .order_by(KaruId.created_at))).scalars().all()
    title, _ = pick_lang(listing.title, locale)
    return await asyncio.to_thread(
        imaging.render_tag_sheet, [(u.code, unit_url(u.code)) for u in units], title=title, maker=profile.public_name,
        scan_local=t("tag.scan", locale), scan_en=t("tag.scan", "en"),
    )


async def product_public(db: AsyncSession, listing: Listing, locale: str, viewer_id: uuid.UUID | None) -> dict:
    from sqlalchemy import func

    from app.core.appconfig import get_config
    from app.modules.catalog.models import Category
    from app.modules.catalog.service import localized, stock_state
    from app.modules.reviews.models import Follow, Review, Wishlist

    profile = await db.get(ArtisanProfile, listing.artisan_id)
    passport = (await db.execute(select(Passport).where(Passport.artisan_id == profile.id))).scalar_one_or_none()
    category = await db.get(Category, listing.category_id) if listing.category_id else None
    craft = await db.get(Craft, listing.craft_id) if listing.craft_id else None
    commerce = await get_config(db, "commerce.v1")
    maker = await public_maker(db, profile, locale)
    if viewer_id:
        maker["following"] = (await db.execute(select(Follow.id).where(Follow.user_id == viewer_id,
                                                                       Follow.artisan_id == profile.id))).first() is not None
    rc, ravg = (await db.execute(select(func.count(), func.avg(Review.rating)).where(
        Review.listing_id == listing.id, Review.status == "published"))).one()
    wished = False
    if viewer_id:
        wished = (await db.execute(select(Wishlist.id).where(Wishlist.user_id == viewer_id,
                                                             Wishlist.listing_id == listing.id))).first() is not None
    # Values left over from a category switch stay editable for the artisan but aren't shown to buyers.
    attrs = attributes.for_category(category.attribute_schema if category else None, listing.attributes)
    return {
        "id": str(listing.id),
        "code": listing.short_code,
        "status": listing.status,
        "title": localized(listing.title, locale, listing.source_lang),
        "description": localized(listing.description, locale, listing.source_lang),
        "price_inr": float(listing.price_inr) if listing.price_inr is not None else None,
        "gallery": await gallery(db, listing),
        "stock": stock_state(listing.quantity_available, commerce["low_stock_threshold"]),
        "returnable": listing.returnable,
        "return_window_days": commerce["return_window_days"],
        "attributes": attrs,
        "tags": listing.tags,
        "category": {"slug": category.slug, "name": pick_lang(category.name, locale)[0]} if category else None,
        "craft": {"slug": craft.slug, "name": pick_lang(craft.name, locale)[0], "gi_tag": craft.gi_tag} if craft else None,
        "verification": await proof_projection(db, listing, locale),
        "maker": maker,
        "maker_suspended": passport is not None and passport.state == "suspended",
        "reviews": {"count": rc or 0, "avg": round(float(ravg), 1) if ravg is not None else None},
        "wishlisted": wished,
        "share_url": short_url(listing),
        "og_image": None,
        "published_at": listing.published_at.isoformat() if listing.published_at else None,
    }
