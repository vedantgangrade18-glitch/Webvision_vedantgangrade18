from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.appconfig import get_config
from app.core.db import utcnow
from app.core.i18n import pick_lang
from app.core.ids import new_handle, new_passport_code
from app.core.storage import get_storage
from app.modules.artisans.models import ArtisanProfile, Passport
from app.modules.verification.scoring import ArtisanRecord


async def create_passport(db: AsyncSession, profile: ArtisanProfile) -> Passport:
    for _ in range(10):
        code = new_passport_code()
        exists = (await db.execute(select(Passport.id).where(Passport.passport_code == code))).first()
        if not exists:
            passport = Passport(artisan_id=profile.id, passport_code=code, state="unverified", last_evaluated_at=utcnow())
            db.add(passport)
            await db.flush()
            return passport
    raise RuntimeError("could not allocate passport code")


async def unique_handle(db: AsyncSession, name: str) -> str:
    for _ in range(10):
        handle = new_handle(name)
        if not (await db.execute(select(ArtisanProfile.id).where(ArtisanProfile.handle == handle))).first():
            return handle
    raise RuntimeError("could not allocate handle")


async def get_passport(db: AsyncSession, artisan_id: uuid.UUID) -> Passport | None:
    return (await db.execute(select(Passport).where(Passport.artisan_id == artisan_id))).scalar_one_or_none()


def profile_completion(p: ArtisanProfile) -> tuple[int, list[str]]:
    """Weights sum to 100; returns (percent, missing items in suggested order)."""
    checks = [
        ("photo", 15, p.profile_photo_media_id is not None),
        ("story", 15, bool(p.story_text) or p.story_voice_media_id is not None),
        ("crafts", 10, bool(p.crafts)),
        ("years", 5, p.years_of_practice is not None),
        ("location", 15, bool(p.district and p.state)),
        ("languages", 5, bool(p.languages)),
        ("aadhaar", 15, p.aadhaar_status == "verified"),
        ("payout", 15, p.payout_status == "active"),
        ("name", 5, bool(p.public_name)),
    ]
    pct = sum(w for _, w, ok in checks if ok)
    return pct, [k for k, _, ok in checks if not ok]


async def artisan_record(db: AsyncSession, artisan_id: uuid.UUID, exclude_listing_id: uuid.UUID | None = None) -> ArtisanRecord:
    from app.modules.admin.models import Report
    from app.modules.catalog.models import Listing
    from app.modules.orders.models import OrderItem, Return
    from app.modules.reviews.models import Review
    from app.modules.verification.models import VerificationRun

    profile = await db.get(ArtisanProfile, artisan_id)
    assert profile is not None
    q_verified = select(func.count()).select_from(Listing).where(
        Listing.artisan_id == artisan_id, Listing.verification_status == "verified", Listing.status != "deleted")
    if exclude_listing_id:
        q_verified = q_verified.where(Listing.id != exclude_listing_id)
    verified = (await db.execute(q_verified)).scalar_one()
    completed = (await db.execute(select(func.count()).select_from(OrderItem).where(
        OrderItem.artisan_id == artisan_id, OrderItem.fulfilment_status.in_(["delivered", "return_requested"])))).scalar_one()
    rc, ravg = (await db.execute(select(func.count(), func.avg(Review.rating)).where(
        Review.artisan_id == artisan_id, Review.status == "published"))).one()
    listing_ids = select(Listing.id).where(Listing.artisan_id == artisan_id)
    id_strings = [str(i) for i in (await db.execute(listing_ids)).scalars().all()]
    fakes = 0
    if id_strings:
        fakes = (await db.execute(select(func.count()).select_from(Report).where(
            Report.target_type == "listing", Report.target_id.in_(id_strings),
            Report.reason == "suspected_fake", Report.status == "confirmed"))).scalar_one()
    q_hf = select(func.count()).select_from(VerificationRun).where(
        VerificationRun.listing_id.in_(listing_ids), VerificationRun.hard_fail.is_(True))
    if exclude_listing_id:
        q_hf = q_hf.where(VerificationRun.listing_id != exclude_listing_id)
    hard_fails = (await db.execute(q_hf)).scalar_one()
    nad = (await db.execute(select(func.count()).select_from(Return).join(OrderItem, Return.order_item_id == OrderItem.id).where(
        OrderItem.artisan_id == artisan_id, Return.reason == "not_as_described", Return.status != "rejected"))).scalar_one()
    return ArtisanRecord(
        aadhaar_verified=profile.aadhaar_status == "verified",
        pehchan_verified=profile.pehchan_status == "verified",
        gi_authorised=bool((profile.gi_registration or {}).get("verified")),
        verified_listings=verified,
        reviews_count=rc or 0,
        avg_rating=float(ravg) if ravg is not None else None,
        completed_orders=completed,
        confirmed_fake_reports=fakes,
        hard_fail_history=hard_fails,
        not_as_described_rate=(nad / completed) if completed else 0.0,
    )


async def passport_checklist(db: AsyncSession, profile: ArtisanProfile) -> dict:
    cfg = await get_config(db, "passport.v1")
    rec = await artisan_record(db, profile.id)
    reviews_ok = rec.reviews_count >= cfg["min_reviews"] and (rec.avg_rating or 0) >= cfg["min_avg_rating"]
    return {
        "aadhaar": profile.aadhaar_status == "verified",
        "one_of": {
            "pehchan": profile.pehchan_status == "verified",
            "verified_product": rec.verified_listings >= 1,
            "reviews": reviews_ok,
        },
        "reviews_count": rec.reviews_count,
        "avg_rating": round(rec.avg_rating, 2) if rec.avg_rating else None,
        "min_reviews": cfg["min_reviews"],
        "min_avg_rating": cfg["min_avg_rating"],
    }


async def evaluate_passport(db: AsyncSession, profile: ArtisanProfile) -> Passport:
    """Part 1 §3.1: verified ⇔ Aadhaar ∧ (Pehchan ∨ ≥1 verified product ∨ ≥5 reviews avg ≥4.0)."""
    passport = await get_passport(db, profile.id)
    assert passport is not None
    passport.last_evaluated_at = utcnow()
    if passport.state == "suspended" or passport.staff_override:
        return passport
    chk = await passport_checklist(db, profile)
    should_verify = chk["aadhaar"] and any(chk["one_of"].values())
    if should_verify and passport.state != "verified":
        passport.state, passport.verified_at, passport.state_reason = "verified", utcnow(), "rules"
        from app.modules.notifications.service import notify

        await notify(db, profile.user_id, "passport_verified", {}, link="/sell/passport")
    elif not should_verify and passport.state == "verified":
        passport.state, passport.state_reason = "unverified", "rules_no_longer_met"
    return passport


async def media_url(db: AsyncSession, media_id: uuid.UUID | None, variant: str = "800_1x1.webp") -> str | None:
    from app.modules.media.models import Media

    if not media_id:
        return None
    m = await db.get(Media, media_id)
    if not m or m.status != "ready":
        return None
    key = (m.variants or {}).get(variant) or m.public_key
    return get_storage().public_url(key) if key else None


def place_of(p: ArtisanProfile) -> str:
    return ", ".join(x for x in [p.village_town, p.district, p.state] if x)


async def public_maker(db: AsyncSession, p: ArtisanProfile, locale: str, *, include_stats: bool = True) -> dict:
    from app.modules.catalog.models import Listing
    from app.modules.reviews.models import Follow, Review

    passport = await get_passport(db, p.id)
    story, story_lang = pick_lang(p.story_text, locale)
    voice_url = None
    if p.show_voice_publicly and p.story_voice_media_id:
        from app.modules.media.models import Media

        m = await db.get(Media, p.story_voice_media_id)
        if m and m.public_key:
            voice_url = get_storage().public_url(m.public_key)
    out = {
        "id": str(p.id),
        "handle": p.handle,
        "name": p.public_name,
        "photo_url": await media_url(db, p.profile_photo_media_id),
        "crafts": p.crafts,
        "years_of_practice": p.years_of_practice,
        "place": place_of(p),
        "district": p.district,
        "state": p.state,
        "languages": p.languages,
        "story": story,
        "story_lang": story_lang,
        "story_translated": bool(story) and story_lang != locale,
        "voice_url": voice_url,
        "passport": {
            "code": passport.passport_code if passport else None,
            "state": passport.state if passport else "unverified",
            "member_since": p.created_at.isoformat(),
        },
    }
    if include_stats:
        verified = (await db.execute(select(func.count()).select_from(Listing).where(
            Listing.artisan_id == p.id, Listing.verification_status == "verified", Listing.status == "published"))).scalar_one()
        rc, ravg = (await db.execute(select(func.count(), func.avg(Review.rating)).where(
            Review.artisan_id == p.id, Review.status == "published"))).one()
        followers = (await db.execute(select(func.count()).select_from(Follow).where(Follow.artisan_id == p.id))).scalar_one()
        out["stats"] = {"verified_products": verified, "reviews": rc or 0,
                        "rating": round(float(ravg), 1) if ravg is not None else None, "followers": followers}
    return out
