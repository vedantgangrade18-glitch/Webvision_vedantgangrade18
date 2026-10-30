"""Live fair-price discovery (Part 1 §3.4, Part 2 §8.1).

fingerprint(category, craft, material, technique, size bucket) → shared benchmark, refreshed
at most every 24 h: TinyFish Search (3–5 queries) → dedupe by domain → Fetch ≤ 12 pages →
LLM (or regex fallback) extracts price + handmade/replica class → IQR outlier removal →
p25/median/p75 per class (≥ 4 samples per class, else "insufficient").
Karu never changes a price; it only advises.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.appconfig import get_config
from app.core.audit import within_budget
from app.core.db import utcnow
from app.core.i18n import format_inr, t
from app.core.jobs import handler, periodic
from app.modules.catalog.models import Category, Craft, Listing
from app.modules.pricing.models import ListingPriceAdvice, PriceBenchmark, PriceSource
from app.providers import fake_context
from app.providers.llm import get_llm
from app.providers.webintel import domain_of, get_webintel

MASS_MARKETPLACES = {"amazon.in", "flipkart.com", "meesho.com", "myntra.com", "ajio.com", "snapdeal.com", "nykaafashion.com",
                     "tatacliq.com", "indiamart.com", "jiomart.com"}
NOUNS = {"sarees": "saree", "dupattas-stoles": "dupatta", "kurtas-fabric": "fabric", "home-textiles": "bedsheet",
         "pottery-terracotta": "pottery", "woodcraft": "wooden handicraft", "metal-brass": "brass handicraft",
         "jewellery": "jewellery", "bamboo-cane": "bamboo basket", "paintings": "painting", "leather": "leather",
         "toys": "wooden toy", "other": "handicraft"}

EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The exact full URL of the page from the URL line above"},
                    "page_index": {"type": "integer", "description": "1-based index of the page in this batch"},
                    "title": {"type": "string"},
                    "price_inr": {"type": "number"},
                    "currency": {"type": "string"},
                    "handmade_claims": {"type": "array", "items": {"type": "string"}},
                    "seller_type": {"type": "string", "enum": ["artisan_or_boutique", "mass_marketplace", "unknown"]},
                    "klass": {"type": "string", "enum": ["handmade", "replica", "unknown"]},
                    "confidence": {"type": "number"},
                },
                "required": ["url", "price_inr", "klass"],
            },
        }
    },
    "required": ["items"],
}


def size_bucket(attrs: dict) -> str:
    dims = attrs.get("dimensions") or {}
    if dims.get("length_m"):
        L = float(dims["length_m"])
        return "len<2" if L < 2 else "len2-4" if L < 4 else "len4-6" if L < 6 else "len6+"
    if dims.get("height_cm"):
        h = float(dims["height_cm"])
        return "h<15" if h < 15 else "h15-40" if h < 40 else "h40+"
    return "na"


def descriptor(listing: Listing, category: Category | None, craft: Craft | None) -> dict:
    attrs = listing.attributes or {}
    return {
        "category": category.slug if category else "other",
        "craft": craft.slug if craft else None,
        "craft_name": (craft.name or {}).get("en") if craft else None,
        "material": (str(attrs.get("material") or "") or None),
        "technique": (str(attrs.get("technique") or "") or None),
        "size": size_bucket(attrs),
    }


def fingerprint(desc_: dict) -> str:
    key = "|".join(str(desc_.get(k) or "").lower() for k in ("category", "craft", "material", "technique", "size"))
    return hashlib.sha1(key.encode()).hexdigest()


def build_queries(d: dict) -> tuple[list[str], list[str]]:
    noun = NOUNS.get(d["category"], "handicraft")
    mat = d.get("material") or ""
    tech = d.get("technique") or "handmade"
    craft = d.get("craft_name") or ""
    handmade = [
        " ".join(x for x in [tech, mat, noun, craft, "price"] if x),
        " ".join(x for x in [craft or tech, noun, "handmade buy online"] if x),
        " ".join(x for x in ["authentic", craft, mat, noun, "artisan"] if x),
    ]
    replica = [" ".join(x for x in [mat, "printed" if d["category"] in ("sarees", "dupattas-stoles", "kurtas-fabric", "home-textiles")
                                    else "machine made", noun, "price"] if x)]
    return handmade, replica


def percentile(values: list[float], p: float) -> float:
    s = sorted(values)
    if not s:
        raise ValueError("empty")
    k = (len(s) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def remove_outliers(values: list[float]) -> list[float]:
    if len(values) < 4:
        return values
    q1, q3 = percentile(values, 0.25), percentile(values, 0.75)
    iqr = q3 - q1
    return [v for v in values if q1 - 1.5 * iqr <= v <= q3 + 1.5 * iqr]


def round_to(value: float, step: int) -> Decimal:
    return Decimal(int(round(value / step)) * step)


async def _extract_prices(pages, *, listing_id, d: dict) -> list[dict]:
    llm = get_llm()
    items: list[dict] = []
    usable = [p for p in pages if not p.error and p.text]
    for i in range(0, len(usable), 4):
        batch = usable[i:i + 4]
        if llm.name == "fake":
            from app.providers.fake_llm_answers import regex_price_extract

            for p in batch:
                for it in regex_price_extract({"text": p.text, "title": p.title})["items"]:
                    if domain_of(p.url) in MASS_MARKETPLACES:
                        it["klass"] = "replica"  # without an LLM, mass-market pages count as the replica range
                    items.append({**it, "url": p.url})
            continue
        prompt = (
            "You extract product prices from web pages for an Indian handmade marketplace. For each page, return the "
            "exact full URL from the page's 'URL:' line above (do NOT shorten or truncate to just the domain), "
            "the 1-based page_index (1 to N), the main product's price in INR (convert only if the page states INR; skip other currencies), "
            "its title, and classify it: 'handmade' if the seller is an artisan, boutique, co-op or GI-tagged source with explicit, "
            "specific handmade/handloom claims; 'replica' if it is a mass-market listing, power-loom, printed, "
            "machine-made or synthetic copy; otherwise 'unknown'. Ignore pages without a single clear product price. "
            f"Product we are benchmarking: {json.dumps(d, ensure_ascii=False)}.\n\n"
            + "\n\n".join(f"### PAGE {j + 1}\nURL: {p.url}\nTITLE: {p.title}\n{p.text[:3500]}" for j, p in enumerate(batch))
        )
        try:
            res = await llm.generate_json(prompt, schema=EXTRACT_SCHEMA, purpose="price_extract", listing_id=listing_id,
                                          fake_context={"page": {"text": batch[0].text, "title": batch[0].title}})
            extracted = res.get("items") or []
            for it in extracted:
                matched_page = None
                p_idx = it.get("page_index")
                if isinstance(p_idx, int) and 1 <= p_idx <= len(batch):
                    matched_page = batch[p_idx - 1]
                if not matched_page:
                    raw_url = (it.get("url") or "").strip()
                    for p in batch:
                        if raw_url == p.url:
                            matched_page = p
                            break
                    if not matched_page and raw_url:
                        for p in batch:
                            if raw_url in p.url or p.url in raw_url:
                                matched_page = p
                                break
                    if not matched_page and raw_url:
                        for p in batch:
                            p_dom = domain_of(p.url)
                            raw_dom = domain_of(raw_url)
                            if p_dom and raw_dom and (p_dom == raw_dom or p_dom in raw_dom or raw_dom in p_dom):
                                matched_page = p
                                break
                    if not matched_page and len(batch) == 1:
                        matched_page = batch[0]
                if matched_page:
                    it["url"] = matched_page.url
                elif it.get("url"):
                    u = it["url"].strip()
                    it["url"] = u if u.startswith(("http://", "https://")) else f"https://{u}"
                items.append(it)
        except Exception:  # noqa: BLE001 - a bad batch should not sink the benchmark
            continue
    return items


async def refresh_benchmark(db: AsyncSession, d: dict, *, listing_id: uuid.UUID | None = None) -> PriceBenchmark:
    cfg = await get_config(db, "pricing.v1")
    fp = fingerprint(d)
    existing = (await db.execute(select(PriceBenchmark).where(PriceBenchmark.fingerprint == fp)
                                 .order_by(desc(PriceBenchmark.refreshed_at)).limit(1))).scalar_one_or_none()
    if not await within_budget(db, "tinyfish"):
        if existing:
            existing.status = "stale"
            return existing
        bm = PriceBenchmark(fingerprint=fp, descriptor=d, status="failed", refreshed_at=None)
        db.add(bm)
        await db.flush()
        return bm

    fake_context.set_category(d["category"])
    web = get_webintel()
    handmade_q, replica_q = build_queries(d)
    seen_domains: set[str] = set()
    urls: list[str] = []
    for q in handmade_q + replica_q:
        try:
            results = await web.search(q, num=10, region="IN", language="en", listing_id=listing_id)
        except Exception:  # noqa: BLE001
            continue
        for r in results:
            dom = domain_of(r.url)
            if dom in seen_domains and dom not in MASS_MARKETPLACES:
                continue
            seen_domains.add(dom)
            urls.append(r.url)
    urls = list(dict.fromkeys(urls))[:12]
    pages = await web.fetch(urls, listing_id=listing_id) if urls else []
    items = await _extract_prices(pages, listing_id=listing_id, d=d)

    now = utcnow()
    sources: list[PriceSource] = []
    for it in items:
        try:
            price = float(it.get("price_inr") or 0)
        except (TypeError, ValueError):
            continue
        if price <= 0 or (it.get("currency") and it.get("currency") not in ("INR", "₹", "Rs")):
            continue
        url = (it.get("url") or "").strip()
        if url and not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        klass = it.get("klass") or "unknown"
        if domain_of(url) in MASS_MARKETPLACES and klass == "unknown":
            klass = "replica"
        sources.append(PriceSource(url=url[:1024], domain=domain_of(url)[:255], title=(it.get("title") or "")[:512],
                                   price_inr=Decimal(str(round(price, 2))), klass=klass,
                                   confidence=float(it.get("confidence") or 0.5), fetched_at=now))

    stats: dict[str, tuple[float, float, float] | None] = {}
    counts: dict[str, int] = {}
    for klass in ("handmade", "replica"):
        vals = [float(s.price_inr) for s in sources if s.klass == klass]
        kept = remove_outliers(vals)
        for s in sources:
            if s.klass == klass and float(s.price_inr) not in kept:
                s.used = False
        counts[klass] = len(kept)
        stats[klass] = (percentile(kept, 0.25), percentile(kept, 0.5), percentile(kept, 0.75)) \
            if len(kept) >= cfg["min_samples_per_class"] else None

    bm = existing or PriceBenchmark(fingerprint=fp, descriptor=d)
    if existing is None:
        db.add(bm)
    bm.descriptor = d
    bm.queries = handmade_q + replica_q
    bm.provider = web.name
    for klass in ("handmade", "replica"):
        s = stats[klass]
        # Market ranges are guidance, not quotes: whole ₹10 steps read better than ₹2,362.50.
        setattr(bm, f"{klass}_p25", Decimal(int(round(s[0], -1))) if s else None)
        setattr(bm, f"{klass}_median", Decimal(int(round(s[1], -1))) if s else None)
        setattr(bm, f"{klass}_p75", Decimal(int(round(s[2], -1))) if s else None)
    bm.sample_size_handmade, bm.sample_size_replica = counts["handmade"], counts["replica"]
    bm.refreshed_at = now
    bm.expires_at = now + timedelta(hours=cfg["cache_hours"])
    bm.status = "fresh" if (stats["handmade"] or stats["replica"]) else "insufficient"
    await db.flush()
    if existing is not None:
        for old in (await db.execute(select(PriceSource).where(PriceSource.benchmark_id == bm.id))).scalars():
            await db.delete(old)
    for s in sources:
        s.benchmark_id = bm.id
        db.add(s)
    await db.flush()
    return bm


async def benchmark_for(db: AsyncSession, listing: Listing, *, refresh_if_stale: bool = True) -> PriceBenchmark | None:
    category = await db.get(Category, listing.category_id) if listing.category_id else None
    craft = await db.get(Craft, listing.craft_id) if listing.craft_id else None
    d = descriptor(listing, category, craft)
    fp = fingerprint(d)
    bm = (await db.execute(select(PriceBenchmark).where(PriceBenchmark.fingerprint == fp)
                           .order_by(desc(PriceBenchmark.refreshed_at)).limit(1))).scalar_one_or_none()
    fresh = bm is not None and bm.expires_at is not None and bm.expires_at > utcnow() and bm.status in ("fresh", "insufficient")
    if not fresh and refresh_if_stale:
        bm = await refresh_benchmark(db, d, listing_id=listing.id)
    return bm


def _range(bm: PriceBenchmark, klass: str) -> dict | None:
    p25, med, p75 = (getattr(bm, f"{klass}_{x}") for x in ("p25", "median", "p75"))
    if p25 is None:
        return None
    return {"p25": float(p25), "median": float(med), "p75": float(p75), "samples": getattr(bm, f"sample_size_{klass}")}


async def compute_advice(db: AsyncSession, listing: Listing, bm: PriceBenchmark | None) -> ListingPriceAdvice:
    cfg = await get_config(db, "pricing.v1")
    basis = "handmade" if listing.verification_status == "verified" else "replica"
    position, suggested, key = "unknown", None, "price.insufficient"
    rng = _range(bm, basis) if bm else None
    if rng is None and bm is not None and basis == "replica":
        # No replica data: fall back to handmade so the artisan still gets guidance.
        rng = _range(bm, "handmade")
        basis = "handmade" if rng else basis
    if rng and listing.price_inr is not None:
        price = float(listing.price_inr)
        position = "below" if price < rng["p25"] else "above" if price > rng["p75"] else "in_range"
        suggested = round_to(rng["median"], cfg["round_to_inr"])
        key = f"price.{position}"
    elif rng:
        suggested = round_to(rng["median"], cfg["round_to_inr"])
        key = "price.in_range"
    advice = ListingPriceAdvice(listing_id=listing.id, benchmark_id=bm.id if bm else None, basis=basis, position=position,
                                suggested_inr=suggested, message_key=key, price_at_advice=listing.price_inr)
    db.add(advice)
    listing.price_position = position
    listing.current_benchmark_id = bm.id if bm else None
    await db.flush()
    return advice


async def advice_view(db: AsyncSession, listing: Listing, locale: str) -> dict:
    advice = (await db.execute(select(ListingPriceAdvice).where(ListingPriceAdvice.listing_id == listing.id)
                               .order_by(desc(ListingPriceAdvice.created_at)).limit(1))).scalar_one_or_none()
    bm = await db.get(PriceBenchmark, advice.benchmark_id) if advice and advice.benchmark_id else None
    if advice is None:
        return {"status": "none"}
    if advice.shown_at is None:
        advice.shown_at = utcnow()
    hand = _range(bm, "handmade") if bm else None
    rep = _range(bm, "replica") if bm else None
    rng = hand if advice.basis == "handmade" else rep
    price = float(listing.price_inr) if listing.price_inr is not None else None
    basis_label = t(f"price.basis.{advice.basis}", locale)
    message = t("price.insufficient", locale)
    if rng:
        message = t(advice.message_key if price is not None else "price.in_range", locale, basis_label=basis_label,
                    low=format_inr(rng["p25"]), high=format_inr(rng["p75"]), price=format_inr(price) if price else "—")
    compare = None
    if listing.verification_status != "verified" and hand and rep:
        compare = t("price.unverified_compare", locale, rlow=format_inr(rep["p25"]), rhigh=format_inr(rep["p75"]),
                    hlow=format_inr(hand["p25"]), hhigh=format_inr(hand["p75"]))
    sources = []
    if bm:
        rows = (await db.execute(select(PriceSource).where(PriceSource.benchmark_id == bm.id, PriceSource.used.is_(True),
                                                           PriceSource.klass == advice.basis)
                                 .order_by(desc(PriceSource.confidence)).limit(5))).scalars().all()
        for s in rows:
            u = (s.url or "").strip()
            if u and not u.startswith(("http://", "https://")):
                u = f"https://{u}"
            sources.append({"site": s.domain, "title": s.title, "price_inr": float(s.price_inr), "url": u or s.domain})
    return {
        "status": bm.status if bm else "insufficient",
        "basis": advice.basis,
        "position": advice.position,
        "price_inr": price,
        "suggested_inr": float(advice.suggested_inr) if advice.suggested_inr is not None else None,
        "handmade": hand,
        "replica": rep,
        "message": message,
        "compare_message": compare,
        "sources": sources,
        "updated_at": bm.refreshed_at.isoformat() if bm and bm.refreshed_at else None,
        "provider": bm.provider if bm else None,
        "accepted": advice.accepted,
    }


async def advise(db: AsyncSession, listing: Listing, *, refresh: bool = True) -> ListingPriceAdvice:
    bm = await benchmark_for(db, listing, refresh_if_stale=refresh)
    return await compute_advice(db, listing, bm)


@handler("pricing.refresh_listing", queue="pricing", max_attempts=2, timeout_s=600)
async def refresh_listing_job(db: AsyncSession, job) -> dict:
    from app.modules.artisans.models import ArtisanProfile
    from app.modules.notifications.service import notify

    listing = await db.get(Listing, uuid.UUID(job.ref_id))
    if listing is None or listing.status not in ("published", "paused", "draft"):
        return {"skipped": True}
    prev = (await db.execute(select(ListingPriceAdvice).where(ListingPriceAdvice.listing_id == listing.id)
                             .order_by(desc(ListingPriceAdvice.created_at)).limit(1))).scalar_one_or_none()
    prev_bm = await db.get(PriceBenchmark, prev.benchmark_id) if prev and prev.benchmark_id else None
    prev_median = getattr(prev_bm, f"{prev.basis}_median", None) if prev and prev_bm else None
    advice = await advise(db, listing, refresh=True)
    bm = await db.get(PriceBenchmark, advice.benchmark_id) if advice.benchmark_id else None
    new_median = getattr(bm, f"{advice.basis}_median", None) if bm else None
    cfg = await get_config(db, "pricing.v1")
    changed = prev is not None and (prev.position != advice.position or (
        prev_median and new_median and abs(float(new_median) - float(prev_median)) / float(prev_median) * 100 > cfg["notify_change_pct"]))
    recently = prev is not None and prev.notified_at and prev.notified_at > utcnow() - timedelta(days=7)
    if changed and not recently and listing.status == "published":
        profile = await db.get(ArtisanProfile, listing.artisan_id)
        title = (listing.title or {}).get(listing.source_lang) or next(iter((listing.title or {}).values()), "")
        await notify(db, profile.user_id, "price_changed", {"title": title}, link=f"/sell/products/{listing.id}?tab=price")
        advice.notified_at = utcnow()
    elif recently and prev:
        advice.notified_at = prev.notified_at
    await db.commit()
    return {"position": advice.position}


@periodic("pricing.refresh_due", every_s=3600)
async def refresh_due(db: AsyncSession) -> None:
    """Daily for active listings, weekly for listings without views in 30 days (§8.1 step 7)."""
    from app.core.jobs import enqueue
    from app.modules.jobs.models import Job

    cfg = await get_config(db, "pricing.v1")
    now = utcnow()
    listings = (await db.execute(select(Listing).where(Listing.status == "published"))).scalars().all()
    for li in listings:
        bm = await db.get(PriceBenchmark, li.current_benchmark_id) if li.current_benchmark_id else None
        idle = li.last_viewed_at is None or li.last_viewed_at < now - timedelta(days=30)
        max_age = timedelta(days=cfg["stale_listing_refresh_days"]) if idle else timedelta(hours=cfg["cache_hours"])
        if bm and bm.refreshed_at and bm.refreshed_at > now - max_age:
            continue
        # Benchmarks are shared by fingerprint, so siblings reuse the first refresh (24 h cache).
        pending = (await db.execute(select(Job.id).where(Job.type == "pricing.refresh_listing", Job.ref_id == str(li.id),
                                                         Job.status.in_(["queued", "running"])))).first()
        if not pending:
            await enqueue(db, "pricing.refresh_listing", ref_type="listing", ref_id=str(li.id))
