from __future__ import annotations

import difflib
import re
import uuid
from collections import defaultdict
from decimal import Decimal

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.appconfig import get_config
from app.core.db import utcnow
from app.core.errors import AppError
from app.core.i18n import pick_lang
from app.core.ids import new_karu_id, new_short_code
from app.core.storage import get_storage
from app.core.translit import phonetic_key
from app.modules.artisans.models import ArtisanProfile, Passport
from app.modules.catalog.models import Category, Craft, Listing, ListingMedia, ListingVersion
from app.modules.karu_ids.models import KaruId, KaruIdEvent
from app.modules.media.models import Media

CORE_ATTRIBUTES = ("material", "technique", "dye")  # changes re-run verification (Part 1 §3.3 rule 6)
PUBLIC_STATUSES = ("published",)


# ---- reference lookups -------------------------------------------------------------------------

async def category_by_slug(db: AsyncSession, slug: str | None) -> Category | None:
    if not slug:
        return None
    return (await db.execute(select(Category).where(Category.slug == slug))).scalar_one_or_none()


async def craft_by_slug(db: AsyncSession, slug: str | None) -> Craft | None:
    if not slug:
        return None
    return (await db.execute(select(Craft).where(Craft.slug == slug))).scalar_one_or_none()


async def all_categories(db: AsyncSession) -> list[Category]:
    return list((await db.execute(select(Category).where(Category.active.is_(True)).order_by(Category.sort))).scalars())


async def unique_short_code(db: AsyncSession) -> str:
    for _ in range(10):
        code = new_short_code()
        if not (await db.execute(select(Listing.id).where(Listing.short_code == code))).first():
            return code
    raise RuntimeError("could not allocate short code")


# ---- media helpers -------------------------------------------------------------------------------

async def listing_media(db: AsyncSession, listing_id: uuid.UUID, roles: tuple[str, ...] | None = None,
                        active_only: bool = True) -> list[tuple[ListingMedia, Media]]:
    q = select(ListingMedia, Media).join(Media, Media.id == ListingMedia.media_id).where(ListingMedia.listing_id == listing_id)
    if roles:
        q = q.where(ListingMedia.role.in_(roles))
    if active_only:
        q = q.where(ListingMedia.active.is_(True))
    return list((await db.execute(q.order_by(ListingMedia.position, ListingMedia.created_at))).all())


def media_urls(m: Media) -> dict:
    st = get_storage()
    v = m.variants or {}

    def u(name):
        return st.public_url(v[name]) if v.get(name) else None

    return {
        "id": str(m.id),
        "thumb": u("400_4x5.webp") or u("400_4x5.jpg"),
        "card": u("800_4x5.webp") or u("800_4x5.jpg") or u("400_4x5.webp") or u("400_4x5.jpg"),
        "large": u("1600_4x5.webp") or u("1600_4x5.jpg") or u("800_4x5.webp") or u("800_4x5.jpg") or u("400_4x5.jpg"),
        "square": u("800_1x1.webp") or u("800_1x1.jpg") or u("400_1x1.jpg"),
        "jpg": u("800_4x5.jpg") or u("400_4x5.jpg"),
        "width": m.width, "height": m.height,
    }


async def gallery(db: AsyncSession, listing: Listing) -> list[dict]:
    """Public gallery: ai_hero first, then enhanced/original photos, then other AI shots."""
    rows = await listing_media(db, listing.id)
    enhanced_by_source = {lm.source_media_id: (lm, m) for lm, m in rows if lm.role == "enhanced_photo"}

    ai_hero_row = next(((lm, m) for lm, m in rows if lm.role == "ai_hero"), None)
    ai_hero_present = ai_hero_row is not None

    real_photos = []
    for lm, m in rows:
        if lm.role != "photo":
            continue
        enh = enhanced_by_source.get(m.id)
        chosen = enh[1] if enh else m
        is_prim = lm.is_primary if not ai_hero_present else False
        real_photos.append({
            **media_urls(chosen),
            "is_primary": is_prim,
            "enhanced": bool(enh),
            "original_id": str(m.id),
            "ai": False,
            "role": "photo",
            "position": lm.position,
        })
    real_photos.sort(key=lambda x: (not x["is_primary"], x.get("position", 0)))
    for r in real_photos:
        r.pop("position", None)

    other_ai_rows = [(lm, m) for lm, m in rows if (lm.role or "").startswith("ai_") and lm.role != "ai_hero"]
    other_ai_rows.sort(key=lambda r: r[0].position)
    other_ai = [{
        **media_urls(m),
        "is_primary": False,
        "enhanced": False,
        "original_id": str(lm.source_media_id or m.id),
        "ai": True,
        "role": lm.role,
    } for lm, m in other_ai_rows]

    out = []
    if ai_hero_row:
        lm, m = ai_hero_row
        out.append({
            **media_urls(m),
            "is_primary": True,
            "enhanced": False,
            "original_id": str(lm.source_media_id or m.id),
            "ai": True,
            "role": lm.role,
        })
    out.extend(real_photos)
    out.extend(other_ai)
    return out


async def primary_images(db: AsyncSession, listing_ids: list[uuid.UUID]) -> dict[uuid.UUID, dict]:
    if not listing_ids:
        return {}
    rows = (await db.execute(
        select(ListingMedia, Media).join(Media, Media.id == ListingMedia.media_id)
        .where(ListingMedia.listing_id.in_(listing_ids), ListingMedia.active.is_(True),
               ListingMedia.role.in_(("photo", "enhanced_photo", "ai_hero")))
        .order_by(ListingMedia.position)
    )).all()
    ai_heroes: dict[uuid.UUID, Media] = {}
    originals: dict[uuid.UUID, tuple[ListingMedia, Media]] = {}
    enhanced: dict[tuple[uuid.UUID, uuid.UUID | None], Media] = {}
    for lm, m in rows:
        if lm.role == "ai_hero":
            ai_heroes[lm.listing_id] = m
        elif lm.role == "enhanced_photo":
            enhanced[(lm.listing_id, lm.source_media_id)] = m
        elif lm.listing_id not in originals or lm.is_primary:
            originals[lm.listing_id] = (lm, m)
    out = {}
    for lid in listing_ids:
        if lid in ai_heroes:
            out[lid] = media_urls(ai_heroes[lid])
        elif lid in originals:
            _, m = originals[lid]
            chosen = enhanced.get((lid, m.id), m)
            out[lid] = media_urls(chosen)
    return out


# ---- search fields & versions ----------------------------------------------------------------------

def build_search_fields(listing: Listing, profile: ArtisanProfile | None, category: Category | None,
                        craft: Craft | None) -> tuple[str, str]:
    a_texts = [*(listing.title or {}).values()]
    b_texts = [*(category.name.values() if category else []), *(craft.name.values() if craft else []),
               profile.public_name if profile else "", *(listing.tags or []),
               *[str(v) for k, v in (listing.attributes or {}).items() if k in ("material", "technique", "dye")],
               profile.district or "" if profile else "", profile.state or "" if profile else ""]
    c_texts = [*(listing.description or {}).values()]
    search_text = " ".join([*a_texts, *b_texts, *c_texts]).lower()
    translit = "A:" + phonetic_key(" ".join(a_texts)) + "|B:" + phonetic_key(" ".join(b_texts)) + "|C:" + phonetic_key(" ".join(c_texts))[:4000]
    return search_text[:20000], translit


def snapshot(listing: Listing, media_ids: list[str]) -> dict:
    return {
        "title": listing.title, "description": listing.description, "attributes": listing.attributes,
        "tags": listing.tags, "price_inr": str(listing.price_inr) if listing.price_inr is not None else None,
        "category_id": str(listing.category_id) if listing.category_id else None,
        "craft_id": str(listing.craft_id) if listing.craft_id else None,
        "returnable": listing.returnable, "media_ids": media_ids,
    }


async def save_version(db: AsyncSession, listing: Listing, changed: list[str], user_id: uuid.UUID | None) -> None:
    media_ids = [str(m.id) for _, m in await listing_media(db, listing.id, ("photo",))]
    db.add(ListingVersion(listing_id=listing.id, version=listing.version, snapshot=snapshot(listing, media_ids),
                          changed_fields=changed, created_by=user_id))


async def refresh_search(db: AsyncSession, listing: Listing) -> None:
    profile = await db.get(ArtisanProfile, listing.artisan_id)
    category = await db.get(Category, listing.category_id) if listing.category_id else None
    craft = await db.get(Craft, listing.craft_id) if listing.craft_id else None
    listing.search_text, listing.translit_text = build_search_fields(listing, profile, category, craft)


# ---- Karu IDs ---------------------------------------------------------------------------------------

async def create_karu_ids(db: AsyncSession, listing: Listing, n: int, actor: uuid.UUID | None) -> list[KaruId]:
    run_id = listing.current_verification_run_id if listing.verification_status == "verified" else None
    created = []
    for _ in range(n):
        for _attempt in range(10):
            code = new_karu_id()
            if not (await db.execute(select(KaruId.id).where(KaruId.code == code))).first():
                break
        else:
            raise RuntimeError("could not allocate Karu ID")
        k = KaruId(code=code, listing_id=listing.id, artisan_id=listing.artisan_id, listing_version=listing.version,
                   status="available", verification_run_id=run_id)
        db.add(k)
        await db.flush()
        db.add(KaruIdEvent(karu_id=k.id, event="created", actor_user_id=actor, data={"listing_version": listing.version}))
        created.append(k)
    await sync_quantity(db, listing)
    return created


async def sync_quantity(db: AsyncSession, listing: Listing) -> None:
    await db.flush()
    rows = (await db.execute(select(KaruId.status, func.count()).where(KaruId.listing_id == listing.id)
                             .group_by(KaruId.status))).all()
    counts = dict(rows)
    listing.quantity_available = counts.get("available", 0)
    listing.quantity_total = sum(v for k, v in counts.items() if k != "retired")


def stock_state(available: int, threshold: int) -> dict:
    if available <= 0:
        return {"state": "out", "count": 0}
    if available <= threshold:
        return {"state": "low", "count": available}
    return {"state": "in", "count": available}


# ---- projections ---------------------------------------------------------------------------------------

def localized(values: dict | None, locale: str, source_lang: str) -> dict:
    text, lang = pick_lang(values, locale)
    return {"text": text, "lang": lang, "translated": bool(text) and lang != source_lang,
            "source_lang": source_lang, "original": (values or {}).get(source_lang)}


async def cards(db: AsyncSession, listings: list[Listing], locale: str, viewer_id: uuid.UUID | None = None) -> list[dict]:
    if not listings:
        return []
    commerce = await get_config(db, "commerce.v1")
    images = await primary_images(db, [li.id for li in listings])
    profiles = {p.id: p for p in (await db.execute(select(ArtisanProfile).where(
        ArtisanProfile.id.in_({li.artisan_id for li in listings})))).scalars()}
    passports = {p.artisan_id: p for p in (await db.execute(select(Passport).where(
        Passport.artisan_id.in_(profiles.keys())))).scalars()}
    wished: set[uuid.UUID] = set()
    if viewer_id:
        from app.modules.reviews.models import Wishlist

        wished = set((await db.execute(select(Wishlist.listing_id).where(
            Wishlist.user_id == viewer_id, Wishlist.listing_id.in_([li.id for li in listings])))).scalars())
    out = []
    for li in listings:
        p = profiles.get(li.artisan_id)
        title, _ = pick_lang(li.title, locale)
        out.append({
            "id": str(li.id), "code": li.short_code, "title": title,
            "price_inr": float(li.price_inr) if li.price_inr is not None else None,
            "image": images.get(li.id),
            "verification": li.verification_status,
            "stock": stock_state(li.quantity_available, commerce["low_stock_threshold"]),
            "maker": {"name": p.public_name if p else "", "handle": p.handle if p else None,
                      "place": ", ".join(x for x in [p.district, p.state] if x) if p else "",
                      "passport_state": passports[p.id].state if p and p.id in passports else "unverified"},
            "rating": round(li.rating_avg, 1) if li.rating_avg else None, "rating_count": li.rating_count,
            "returnable": li.returnable, "wishlisted": li.id in wished,
        })
    return out


async def latest_run(db: AsyncSession, listing: Listing):
    from app.modules.verification.models import VerificationRun

    if listing.current_verification_run_id:
        run = await db.get(VerificationRun, listing.current_verification_run_id)
        if run:
            return run
    return (await db.execute(select(VerificationRun).where(VerificationRun.listing_id == listing.id)
                             .order_by(desc(VerificationRun.created_at)).limit(1))).scalar_one_or_none()


async def proof_projection(db: AsyncSession, listing: Listing, locale: str) -> dict:
    """What buyers see (Part 1 §3.3 rule 5): verdict + three plain checks, never numbers."""
    from app.core.i18n import format_date
    from app.modules.verification.models import ImageMatch

    run = await latest_run(db, listing)
    profile = await db.get(ArtisanProfile, listing.artisan_id)
    status = listing.verification_status
    out: dict = {"status": status, "checks": [], "making_video": None, "registry": [], "photos_original": None,
                 "verified_on": None, "revoked_on": None}
    if run and run.status == "completed":
        cfg = run.config_snapshot or {}
        floors = cfg.get("floors", {"L1": 40, "L3": 50})
        out["checks"] = [
            {"key": "handmade_look", "state": "passed" if (run.l1_score or 0) >= max(floors.get("L1", 40), 60) else "not_passed"},
            {"key": "maker_record", "state": "new_maker" if run.l2_mode == "new_artisan_constant" else
             ("passed" if (run.l2_score or 0) >= 50 else "not_passed")},
            {"key": "making_video", "state": "passed" if (run.l3_score or 0) >= floors.get("L3", 50) else
             ("missing" if not run.l3_score else "not_passed")},
        ]
        if status == "verified":
            out["verified_on"] = format_date(run.completed_at, locale)
            matches = (await db.execute(select(func.count()).select_from(ImageMatch).where(
                ImageMatch.run_id == run.id, ImageMatch.is_own_channel.is_(False)))).scalar_one()
            out["photos_original"] = matches == 0 and "web_originality" not in (run.deferred_checks or [])
    elif status == "checking":
        out["checks"] = [{"key": k, "state": "pending"} for k in ("handmade_look", "maker_record", "making_video")]
    if status == "revoked":
        out["revoked_on"] = format_date(listing.updated_at, locale)
    if status == "verified":
        vids = await listing_media(db, listing.id, ("making_video",))
        if vids and vids[-1][1].public_key:
            m = vids[-1][1]
            st = get_storage()
            out["making_video"] = {"url": st.public_url(m.public_key), "duration_s": m.duration_s,
                                   "poster": st.public_url(m.variants["poster.jpg"]) if (m.variants or {}).get("poster.jpg") else None}
    if profile and profile.pehchan_status == "verified" and profile.pehchan_checked_at:
        out["registry"].append({"kind": "pehchan", "date": format_date(profile.pehchan_checked_at, locale)})
    if profile and (profile.gi_registration or {}).get("verified"):
        out["registry"].append({"kind": "gi", "date": format_date(profile.updated_at, locale),
                                "detail": profile.gi_registration.get("product")})
    return out


async def similar_listings(db: AsyncSession, listing: Listing, limit: int = 8) -> list[Listing]:
    """Nearest neighbours on the primary-photo embedding within the category (Part 2 §9.6)."""
    from app.core.imaging import cosine

    q = (select(Listing).where(Listing.status == "published", Listing.hidden_by_staff.is_(False), Listing.id != listing.id)
         .order_by(desc(Listing.published_at)).limit(400))
    if listing.category_id:
        q = q.where(Listing.category_id == listing.category_id)
    candidates = list((await db.execute(q)).scalars())
    scored = sorted(candidates, key=lambda c: cosine(listing.image_embedding, c.image_embedding)
                    + (0.15 if c.craft_id and c.craft_id == listing.craft_id else 0), reverse=True)
    return scored[:limit]


# ---- search -----------------------------------------------------------------------------------------------

_FIELD_WEIGHTS = {"A": 1.0, "B": 0.6, "C": 0.3}


def _parse_translit(text: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {"A": [], "B": [], "C": []}
    for part in (text or "").split("|"):
        if len(part) > 2 and part[1] == ":" and part[0] in out:
            out[part[0]] = part[2:].split()
    return out


def _token_match(q: str, words: list[str]) -> float:
    best = 0.0
    for w in words:
        if w == q:
            return 1.0
        if len(q) >= 3 and (w.startswith(q) or q.startswith(w) and len(w) >= 4):
            best = max(best, 0.85)
        elif abs(len(w) - len(q)) <= 3 and len(q) >= 4:
            r = difflib.SequenceMatcher(None, q, w).ratio()
            if r >= 0.78:
                best = max(best, r * 0.9)
    return best


def relevance(query_keys: list[str], translit_text: str) -> float:
    fields = _parse_translit(translit_text)
    total, matched = 0.0, 0
    for q in query_keys:
        s = max(_token_match(q, fields[f]) * w for f, w in _FIELD_WEIGHTS.items())
        if s > 0:
            matched += 1
        total += s
    if not query_keys or matched < max(1, (len(query_keys) + 1) // 2):
        return 0.0
    return total / len(query_keys)


async def search(db: AsyncSession, *, q: str | None, category: str | None = None, craft: str | None = None,
                 state: str | None = None, material: str | None = None, verified_only: bool = False,
                 returnable: bool | None = None, in_stock: bool | None = None, min_price: float | None = None,
                 max_price: float | None = None, min_rating: float | None = None, maker_handle: str | None = None,
                 sort: str = "relevance", offset: int = 0, limit: int = 24) -> tuple[list[Listing], int, dict]:
    stmt = (select(Listing).join(Passport, Passport.artisan_id == Listing.artisan_id)
            .join(ArtisanProfile, ArtisanProfile.id == Listing.artisan_id)
            .where(Listing.status == "published", Listing.hidden_by_staff.is_(False), Passport.state != "suspended"))
    if category:
        cat = await category_by_slug(db, category)
        if not cat:
            return [], 0, {}
        stmt = stmt.where(Listing.category_id == cat.id)
    if craft:
        cr = await craft_by_slug(db, craft)
        if not cr:
            return [], 0, {}
        stmt = stmt.where(Listing.craft_id == cr.id)
    if state:
        stmt = stmt.where(func.lower(ArtisanProfile.state) == state.lower())
    if maker_handle:
        stmt = stmt.where(ArtisanProfile.handle == maker_handle)
    if verified_only:
        stmt = stmt.where(Listing.verification_status == "verified")
    if returnable is not None:
        stmt = stmt.where(Listing.returnable.is_(returnable))
    if in_stock:
        stmt = stmt.where(Listing.quantity_available > 0)
    if min_price is not None:
        stmt = stmt.where(Listing.price_inr >= Decimal(str(min_price)))
    if max_price is not None:
        stmt = stmt.where(Listing.price_inr <= Decimal(str(max_price)))
    if min_rating is not None:
        stmt = stmt.where(Listing.rating_avg >= min_rating)
    candidates = list((await db.execute(stmt.order_by(desc(Listing.published_at)).limit(5000))).scalars())
    if material:
        candidates = [c for c in candidates if str((c.attributes or {}).get("material", "")).lower() == material.lower()]

    facets: dict = {"materials": defaultdict(int), "states": defaultdict(int), "verified": 0}
    scored: list[tuple[float, Listing]] = []
    keys = phonetic_key(q).split() if q else []
    raw = [w for w in re.findall(r"\w+", (q or "").lower()) if len(w) > 1]
    for li in candidates:
        if keys:
            rel = relevance(keys, li.translit_text)
            if rel == 0 and raw and all(w in li.search_text for w in raw):
                rel = 0.5
            if rel == 0:
                continue
        else:
            rel = 1.0
        boost = 1.0
        if li.verification_status == "verified":
            boost *= 1.3
        if li.quantity_available > 0:
            boost *= 1.1
        if li.rating_avg:
            boost *= 1 + (li.rating_avg - 3) * 0.05
        scored.append((rel * boost, li))
        mat = (li.attributes or {}).get("material")
        if mat:
            facets["materials"][str(mat)] += 1
        if li.verification_status == "verified":
            facets["verified"] += 1
    if sort == "new":
        scored.sort(key=lambda x: x[1].published_at or utcnow(), reverse=True)
    elif sort == "price_asc":
        scored.sort(key=lambda x: x[1].price_inr or 0)
    elif sort == "price_desc":
        scored.sort(key=lambda x: x[1].price_inr or 0, reverse=True)
    elif sort == "rating":
        scored.sort(key=lambda x: (x[1].rating_avg or 0, x[1].rating_count), reverse=True)
    else:
        scored.sort(key=lambda x: (x[0], x[1].published_at or utcnow()), reverse=True)
    total = len(scored)
    page = [li for _, li in scored[offset:offset + limit]]
    facets["materials"] = dict(facets["materials"])
    facets.pop("states")
    return page, total, facets


async def assert_owner(db: AsyncSession, listing_id: uuid.UUID | str, artisan: ArtisanProfile) -> Listing:
    try:
        lid = uuid.UUID(str(listing_id))
    except ValueError:
        raise AppError(404, "listing_not_found") from None
    listing = await db.get(Listing, lid)
    if listing is None or listing.artisan_id != artisan.id or listing.status == "deleted":
        raise AppError(404, "listing_not_found")
    return listing
