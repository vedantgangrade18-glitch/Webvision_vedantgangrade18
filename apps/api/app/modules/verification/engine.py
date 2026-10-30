"""Three-layer verification engine (Part 1 §3.3, Part 2 §7).

A run covers one listing version (the batch). L1 and L3 run concurrently, each with its
own DB session; L2 is computed from records. The Karu Score decides; hard fails block
verification and raise a staff flag. A listing always stays published whatever happens.
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from urllib.parse import urlparse

import httpx
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import imaging, video
from app.core.appconfig import get_config
from app.core.audit import within_budget
from app.core.db import sessionmaker, utcnow
from app.core.jobs import enqueue, handler, on_failure, periodic
from app.core.storage import get_storage
from app.modules.artisans.models import ArtisanProfile
from app.modules.artisans.service import artisan_record, evaluate_passport
from app.modules.catalog.models import Category, Listing, ListingMedia
from app.modules.catalog.service import listing_media
from app.modules.karu_ids.models import KaruId, KaruIdEvent
from app.modules.media.models import Media
from app.modules.verification import scoring
from app.modules.verification.models import EvidenceItem, ImageMatch, VerificationLayerResult, VerificationRun
from app.providers.llm import get_llm
from app.providers.webintel import domain_of, get_webintel

log = logging.getLogger("karu.verification")

RUBRICS = {
    "textiles": "For handloom/hand-embroidered/hand-printed textiles look for: slight irregularities in the weave, uneven "
                "slubs, selvedge finish, variance in motif repetition, hand-knotted or hand-finished fringes, block "
                "registration offsets. Against: perfectly identical repeats, digital-print sharpness, synthetic sheen, "
                "machine-stitched selvedges.",
    "ceramics": "For pottery/terracotta look for: wheel marks, slight asymmetry, glaze pooling and variance, hand-applied "
                "decoration, thumb marks. Against: mould seams, perfectly uniform glaze, decals.",
    "wood": "For wood/bamboo/cane look for: tool marks, hand carving variance, natural grain alignment, hand-woven "
            "irregularity. Against: CNC precision, laminate, plastic.",
    "metal": "For metal/dokra/brass look for: casting texture, hand-chased detail, slight asymmetry, wax-thread "
             "patterns. Against: die-cast uniformity, electroplated sheen.",
    "paintings": "For paintings look for: brush strokes, pigment texture, hand-drawn line variance, paper/cloth texture. "
                 "Against: print dot patterns, perfectly uniform fills, glossy print surface.",
    "general": "Look for evidence of hand work (tool marks, variance, hand finishing) versus machine uniformity, moulding "
               "or printing.",
}
CATEGORY_GROUP = {"sarees": "textiles", "dupattas-stoles": "textiles", "kurtas-fabric": "textiles", "home-textiles": "textiles",
                  "pottery-terracotta": "ceramics", "woodcraft": "wood", "bamboo-cane": "wood", "toys": "wood",
                  "metal-brass": "metal", "jewellery": "metal", "paintings": "paintings"}

L1_SCHEMA = {"type": "object", "properties": {
    "handmade_probability": {"type": "number"},
    "cues_for": {"type": "array", "items": {"type": "string"}},
    "cues_against": {"type": "array", "items": {"type": "string"}},
}, "required": ["handmade_probability", "cues_for", "cues_against"]}

L3_SCHEMA = {"type": "object", "properties": {
    "process_score": {"type": "number"},
    "shows_hands_at_work": {"type": "boolean"},
    "shows_tools": {"type": "boolean"},
    "technique_matches_claim": {"type": "boolean"},
    "same_item_as_photos": {"type": "boolean"},
    "same_item_confidence": {"type": "number"},
    "minor_visible": {"type": "boolean"},
    "evidence": {"type": "array", "items": {"type": "object", "properties": {
        "t_s": {"type": "number"}, "cue": {"type": "string"}}}},
}, "required": ["process_score", "same_item_as_photos", "same_item_confidence", "minor_visible"]}


@dataclass
class LayerOut:
    score: float | None
    sub_scores: dict = field(default_factory=dict)
    evidence: dict = field(default_factory=dict)
    hard_fail_reason: str | None = None
    deferred: list[str] = field(default_factory=list)
    matches: list[dict] = field(default_factory=list)
    models: dict = field(default_factory=dict)
    flags: list[str] = field(default_factory=list)


# ---- helpers ---------------------------------------------------------------------------------------------

def _public_host(url: str) -> bool:
    """SSRF guard for fetching third-party images."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return False
        for info in socket.getaddrinfo(parsed.hostname, None):
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                return False
        return True
    except (OSError, ValueError):
        return False


async def _download_image_hashes(urls: list[str], limit: int = 12) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []

    async def one(client: httpx.AsyncClient, url: str):
        if not await asyncio.to_thread(_public_host, url):
            return
        try:
            resp = await client.get(url)
            if resp.status_code != 200 or len(resp.content) > 4 * 1024 * 1024:
                return
            if imaging.sniff_mime(resp.content) not in ("image/jpeg", "image/png", "image/webp"):
                return
            img = await asyncio.to_thread(imaging.load_image, resp.content)
            if min(img.size) < 120:
                return
            out.append((url, imaging.phash(img)))
        except Exception:  # noqa: BLE001
            return

    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0), follow_redirects=True,
                                 headers={"User-Agent": "KaruVerification/1.0 (+https://karu.ai)"}) as client:
        await asyncio.gather(*(one(client, u) for u in urls[:limit]))
    return out


def _own_channel(domain: str, linked: list[str]) -> bool:
    for url in linked or []:
        d = domain_of(url if "://" in url else f"https://{url}")
        if d and (domain == d or domain.endswith("." + d)):
            return True
    return False


async def _web_image_matches(listing: Listing, phashes: list[tuple[uuid.UUID, str, datetime]], linked: list[str],
                             run_id: uuid.UUID, threshold: int) -> tuple[list[dict], list[str]]:
    """Search the web by product text, fetch result pages, compare page images by pHash."""
    web = get_webintel()
    title_en = (listing.title or {}).get("en") or next(iter((listing.title or {}).values()), "")
    attrs = listing.attributes or {}
    q = " ".join(x for x in [title_en, str(attrs.get("material") or ""), str(attrs.get("technique") or "")] if x)[:200]
    results = await web.search(q, num=8, listing_id=listing.id, run_id=run_id)
    pages = await web.fetch([r.url for r in results[:5]], image_links=True, listing_id=listing.id, run_id=run_id)
    matches: list[dict] = []
    for page in pages:
        if page.error or not page.image_links:
            continue
        hashes = await _download_image_hashes(page.image_links)
        dom = domain_of(page.url)
        for img_url, h in hashes:
            for media_id, ph, uploaded_at in phashes:
                dist = imaging.hamming(ph, h)
                if dist <= threshold + 4:
                    matches.append({"media_id": media_id, "url": img_url, "page": page.url, "domain": dom,
                                    "distance": dist, "own": _own_channel(dom, linked),
                                    "published": page.published_date, "uploaded_at": uploaded_at})
    return matches, []


def _predates(published: str | None, uploaded_at: datetime) -> bool:
    if not published:
        return False
    try:
        dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
    except ValueError:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=uploaded_at.tzinfo)
    return dt < uploaded_at


# ---- L1 ----------------------------------------------------------------------------------------------------

async def run_l1(listing_id: uuid.UUID, run_id: uuid.UUID, cfg: dict) -> LayerOut:
    async with sessionmaker()() as db:
        listing = await db.get(Listing, listing_id)
        profile = await db.get(ArtisanProfile, listing.artisan_id)
        rows = await listing_media(db, listing_id, ("photo",))
        if not rows:
            return LayerOut(None, {"quality_failed": True}, {"reason": "no_photos"})
        primary = next((m for lm, m in rows if lm.is_primary), rows[0][1])
        q = primary.quality or {}
        out = LayerOut(None)
        out.sub_scores["quality"] = q
        if not q.get("ok", True):
            out.sub_scores["quality_failed"] = True
            return out
        category = await db.get(Category, listing.category_id) if listing.category_id else None
        group = CATEGORY_GROUP.get(category.slug if category else "", "general")
        st = get_storage()
        photos = []
        for _, m in rows[:3]:
            img = await asyncio.to_thread(imaging.load_image, await st.get_private(m.storage_key))
            photos.append((await asyncio.to_thread(imaging.compress_for_llm, img), "image/jpeg"))
        llm = get_llm()
        rubric = await llm.generate_json(
            "You are an expert in Indian handmade crafts helping verify whether a product is genuinely handmade. "
            f"Category: {category.slug if category else 'unknown'}. Claimed technique: "
            f"{(listing.attributes or {}).get('technique', 'unknown')}. {RUBRICS[group]} Judge only what is visible. "
            "Return handmade_probability between 0 and 1, plus short visual cues for and against.",
            schema=L1_SCHEMA, purpose="l1_rubric", images=photos, temperature=0.0, listing_id=listing_id, run_id=run_id,
            fake_context={"seed": primary.sha256 or str(primary.id)},
        )
        h = max(0.0, min(1.0, float(rubric.get("handmade_probability", 0))))
        out.sub_scores["handmade_probability"] = h
        out.evidence["rubric"] = {"cues_for": rubric.get("cues_for", []), "cues_against": rubric.get("cues_against", []),
                                  "provider": rubric.get("provider", llm.name)}
        out.models["l1"] = rubric.get("_model", llm.name)

        # Originality — internal
        threshold = cfg["l1"]["phash_match_hamming"]
        penalty = 0.0
        mine = [(m.id, m.phash, m.created_at) for _, m in rows if m.phash]
        others = (await db.execute(select(Media.id, Media.phash, Media.owner_user_id, Media.created_at).where(
            Media.kind == "photo", Media.phash.is_not(None), Media.owner_user_id != profile.user_id,
            Media.status == "ready"))).all()
        for mid, ph, uploaded in mine:
            for oid, oph, _owner, ocreated in others:
                dist = imaging.hamming(ph, oph)
                if dist <= threshold:
                    out.matches.append({"media_id": mid, "url": f"internal:{oid}", "domain": "karu.ai", "distance": dist,
                                        "own": False, "internal_media_id": oid})
                    if ocreated < uploaded:
                        out.hard_fail_reason = "photo_belongs_to_another_artisan"
        # Originality — external (TinyFish), behind the daily budget breaker
        if await within_budget(db, "tinyfish"):
            try:
                ext, _ = await _web_image_matches(listing, mine, profile.linked_social_urls, run_id, threshold)
                for mt in ext:
                    out.matches.append(mt)
                    if mt["own"]:
                        continue
                    if mt["distance"] <= threshold:
                        if _predates(mt.get("published"), mt["uploaded_at"]):
                            out.hard_fail_reason = out.hard_fail_reason or "photo_found_elsewhere_earlier"
                        penalty = max(penalty, 25)
                    else:
                        penalty = max(penalty, 10)
            except Exception as exc:  # noqa: BLE001
                log.warning("web originality failed: %s", exc)
                out.deferred.append("web_originality")
        else:
            out.deferred.append("web_originality")
        out.sub_scores["originality_penalty"] = penalty
        out.score = scoring.l1_score(h, penalty, cfg["l1"]["max_originality_penalty"])
        return out


# ---- L3 ----------------------------------------------------------------------------------------------------

async def run_l3(listing_id: uuid.UUID, run_id: uuid.UUID, cfg: dict) -> LayerOut:
    async with sessionmaker()() as db:
        listing = await db.get(Listing, listing_id)
        vids = await listing_media(db, listing_id, ("making_video",))
        if not vids:
            return LayerOut(0.0, {"has_video": False})
        lm_v, vmedia = vids[-1]
        out = LayerOut(None, {"has_video": True})
        st = get_storage()
        data = await st.get_private(vmedia.storage_key)
        l3cfg = cfg["l3"]
        frames = await video.keyframes(data, l3cfg["max_keyframes"])
        fp = video.fingerprint(frames, data)
        vmedia.video_fingerprint = fp
        out.sub_scores["keyframes"] = len(frames)
        out.sub_scores["duration_s"] = vmedia.duration_s

        # Originality: same video on a different listing → hard fail (siblings of the same design allowed)
        originality = 100.0
        prow = await listing_media(db, listing_id, ("photo",))
        my_primary = next((m for lm, m in prow if lm.is_primary), prow[0][1] if prow else None)
        others = (await db.execute(
            select(Media, ListingMedia.listing_id).join(ListingMedia, ListingMedia.media_id == Media.id).where(
                ListingMedia.role == "making_video", ListingMedia.listing_id != listing_id, Media.video_fingerprint.is_not(None))
        )).all()
        for om, other_listing_id in others:
            sim = video.fingerprint_similarity(fp, om.video_fingerprint)
            if sim < 0.8:
                continue
            other = await db.get(Listing, other_listing_id)
            sibling = False
            if other and other.artisan_id == listing.artisan_id and my_primary:
                orows = await listing_media(db, other.id, ("photo",))
                op = next((m for lm, m in orows if lm.is_primary), orows[0][1] if orows else None)
                sibling = op is not None and imaging.hamming(op.phash, my_primary.phash) <= 10
            out.evidence.setdefault("video_reuse", []).append({"listing_id": str(other_listing_id), "similarity": sim,
                                                               "sibling": sibling})
            if not sibling:
                out.hard_fail_reason = "making_video_reused"
        # Web check on 3 sampled frames
        if frames and await within_budget(db, "tinyfish"):
            try:
                sample = [frames[i] for i in sorted({0, len(frames) // 2, len(frames) - 1})]
                fake_ids = [(uuid.uuid4(), imaging.phash(f), vmedia.created_at) for f in sample]
                prof = await db.get(ArtisanProfile, listing.artisan_id)
                ext, _ = await _web_image_matches(listing, fake_ids, prof.linked_social_urls, run_id, 8)
                foreign = [m for m in ext if not m["own"] and m["distance"] <= 8]
                if foreign:
                    originality -= 60
                    out.evidence["web_frame_matches"] = [{"url": m["url"], "domain": m["domain"]} for m in foreign[:5]]
            except Exception as exc:  # noqa: BLE001
                log.warning("video web check failed: %s", exc)
                out.deferred.append("web_video_originality")
        elif frames:
            out.deferred.append("web_video_originality")
        originality = max(0.0, originality)

        # Process + product match (Gemini video understanding on a low-res proxy, or keyframes)
        category = await db.get(Category, listing.category_id) if listing.category_id else None
        photos = []
        for _, m in prow[:2]:
            img = await asyncio.to_thread(imaging.load_image, await st.get_private(m.storage_key))
            photos.append((await asyncio.to_thread(imaging.compress_for_llm, img, 768), "image/jpeg"))
        prox = await video.proxy(data)
        llm = get_llm()
        kwargs: dict = {"images": photos}
        if prox:
            kwargs["video"] = prox
        elif frames:
            step = max(1, len(frames) // 6)
            kwargs["images"] = photos + [(imaging.compress_for_llm(f, 512), "image/jpeg") for f in frames[::step][:6]]
        res = await llm.generate_json(
            "This is an artisan's 'making video' submitted to prove a product is handmade. The first images are the "
            "product listing photos" + (", followed by frames from the video" if "video" not in kwargs else "") + ". "
            f"Claimed craft/technique: {(listing.attributes or {}).get('technique', 'unknown')} "
            f"({category.slug if category else 'unknown category'}). Score process_score 0–100 for how clearly it shows "
            "the claimed process by hand (hands at work, tools/loom/wheel, work-in-progress). Decide whether the finished "
            "item shown matches the listing photos (same design and colour). Set minor_visible=true if a child appears to "
            "be working. Give evidence with timestamps.",
            schema=L3_SCHEMA, purpose="l3_video", temperature=0.0, listing_id=listing_id, run_id=run_id,
            fake_context={"seed": vmedia.sha256 or str(vmedia.id)}, **kwargs,
        )
        process = max(0.0, min(100.0, float(res.get("process_score", 0))))
        conf = max(0.0, min(1.0, float(res.get("same_item_confidence", 0.5))))
        llm_match = 100 * conf if res.get("same_item_as_photos") else 100 * (1 - conf) * 0.5
        match = llm_match
        if frames and prow:
            best = 0.0
            for f in frames[:: max(1, len(frames) // 30)]:
                emb = imaging.lite_embedding(f)
                for _, pm in prow:
                    best = max(best, imaging.cosine(emb, pm.embedding))
            emb_score = scoring.similarity_to_match_score(best)
            match = round(0.5 * emb_score + 0.5 * llm_match, 2)
            out.sub_scores["embedding_similarity"] = round(best, 4)
        out.sub_scores.update({"process": round(process, 2), "match": round(match, 2), "originality": originality})
        out.evidence["video_analysis"] = {k: res.get(k) for k in ("shows_hands_at_work", "shows_tools",
                                                                  "technique_matches_claim", "evidence")}
        out.evidence["provider"] = res.get("provider", llm.name)
        out.models["l3"] = res.get("_model", llm.name)
        if res.get("minor_visible"):
            out.flags.append("minor_visible")
        out.score = scoring.l3_score(process, match, originality, l3cfg["weights"])
        await db.commit()  # persist the fingerprint
        return out


# ---- orchestration ------------------------------------------------------------------------------------------

async def start_run(db: AsyncSession, listing: Listing, triggered_by: str) -> VerificationRun:
    cfg = await get_config(db, "verification.v1")
    run = VerificationRun(listing_id=listing.id, listing_version=listing.version, triggered_by=triggered_by,
                          status="queued", config_snapshot=cfg)
    db.add(run)
    await db.flush()
    if triggered_by != "periodic":
        listing.verification_status = "checking"
        listing.current_verification_run_id = run.id
    await enqueue(db, "verification.run", ref_type="verification_run", ref_id=str(run.id),
                  payload={"run_id": str(run.id)})
    return run


@handler("verification.run", queue="verification", max_attempts=3, timeout_s=900)
async def run_verification(db: AsyncSession, job) -> dict:
    run = await db.get(VerificationRun, uuid.UUID(job.payload["run_id"]))
    if run is None or run.status == "completed":
        return {"skipped": True}
    listing = await db.get(Listing, run.listing_id)
    if listing is None:
        return {"skipped": True}
    run.status, run.started_at, run.attempts = "running", utcnow(), run.attempts + 1
    await db.commit()
    cfg = run.config_snapshot

    l1_task = asyncio.create_task(run_l1(listing.id, run.id, cfg))
    l3_task = asyncio.create_task(run_l3(listing.id, run.id, cfg))
    rec = await artisan_record(db, listing.artisan_id, exclude_listing_id=listing.id)
    l2 = scoring.l2_score(rec, cfg["new_artisan_l2_constant"])
    l1, l3 = await asyncio.gather(l1_task, l3_task)
    await db.refresh(run)
    await db.refresh(listing)

    hard_reason = l1.hard_fail_reason or l3.hard_fail_reason
    l1_value = l1.score if l1.score is not None else 0.0
    decision = scoring.decide(l1_value, l2.score, l3.score, hard_fail=bool(hard_reason), cfg=cfg)
    tips, layer_status = scoring.artisan_tips(
        l1_value, l2.score, l3.score, has_video=l3.sub_scores.get("has_video", False),
        aadhaar_verified=rec.aadhaar_verified, l1_quality_failed=bool(l1.sub_scores.get("quality_failed")),
        hard_fail=bool(hard_reason), l3_detail=l3.sub_scores, cfg=cfg)

    run.l1_score, run.l2_score, run.l3_score = l1.score, l2.score, l3.score
    run.l2_mode = l2.mode
    run.karu_score = decision.karu_score
    run.verdict = decision.verdict
    run.hard_fail, run.hard_fail_reason = bool(hard_reason), hard_reason
    run.artisan_tips, run.layer_status = tips, layer_status
    run.deferred_checks = l1.deferred + l3.deferred
    for layer, res in (("L1", l1), ("L2", None), ("L3", l3)):
        if res is None:
            db.add(VerificationLayerResult(run_id=run.id, layer="L2", score=l2.score, sub_scores=l2.parts,
                                           evidence={"mode": l2.mode, "record": rec.__dict__}))
        else:
            db.add(VerificationLayerResult(run_id=run.id, layer=layer, score=res.score, sub_scores=res.sub_scores,
                                           evidence=res.evidence, model_versions=res.models))
    for mt in l1.matches:
        db.add(ImageMatch(run_id=run.id, media_id=mt["media_id"], matched_url=mt["url"][:1024], matched_domain=mt["domain"][:255],
                          matched_media_id=mt.get("internal_media_id"), similarity=round(1 - mt["distance"] / 64, 4),
                          is_own_channel=mt["own"]))
    if l3.evidence.get("video_analysis"):
        db.add(EvidenceItem(run_id=run.id, kind="video_analysis", captured_at=utcnow(), summary=l3.evidence))
    run.status, run.completed_at = "completed", utcnow()

    await apply_outcome(db, listing, run, l3_flags=l3.flags)
    await db.commit()
    return {"verdict": run.verdict, "hard_fail": run.hard_fail}


async def apply_outcome(db: AsyncSession, listing: Listing, run: VerificationRun, *, l3_flags: list[str] | None = None) -> None:
    from app.core.revalidate import revalidate_listing
    from app.modules.admin.models import Report
    from app.modules.notifications.service import notify
    from app.modules.pricing.service import advise

    profile = await db.get(ArtisanProfile, listing.artisan_id)
    title = (listing.title or {}).get(listing.source_lang) or next(iter((listing.title or {}).values()), "")
    periodic_run = run.triggered_by == "periodic"
    stale = listing.version != run.listing_version  # edited while running → a newer run will decide

    if run.hard_fail:
        db.add(Report(target_type="listing", target_id=str(listing.id), reason="hard_fail", source="system",
                      details=run.hard_fail_reason))
    if "minor_visible" in (l3_flags or []):
        db.add(Report(target_type="listing", target_id=str(listing.id), reason="child_labour", source="system",
                      details="Making video may show a minor working; review required (Part 1 §10)."))

    if stale:
        return
    if periodic_run:
        if run.hard_fail and listing.verification_status == "verified":
            await revoke(db, listing, reason=run.hard_fail_reason or "periodic_rescan")
        return

    listing.current_verification_run_id = run.id
    if run.verdict == "verified":
        listing.verification_status = "verified"
        listing.verified_version = listing.version
        units = (await db.execute(select(KaruId).where(KaruId.listing_id == listing.id, KaruId.status != "retired"))).scalars().all()
        for k in units:
            if k.listing_version == listing.version or k.status == "available":
                k.verification_run_id = run.id
                db.add(KaruIdEvent(karu_id=k.id, event="verified", data={"run_id": str(run.id)}))
        await _publish_making_video(db, listing, profile)
        await notify(db, profile.user_id, "verification_verified", {"title": title}, link=f"/sell/products/{listing.id}?tab=share")
    else:
        listing.verification_status = "not_verified"
        units = (await db.execute(select(KaruId).where(KaruId.listing_id == listing.id, KaruId.status == "available"))).scalars().all()
        for k in units:
            k.verification_run_id = None
        await notify(db, profile.user_id, "verification_not_verified", {"title": title},
                     link=f"/sell/products/{listing.id}?tab=verification")
    await evaluate_passport(db, profile)
    try:
        await advise(db, listing, refresh=False)  # basis switches handmade ↔ replica
    except Exception:  # noqa: BLE001
        pass
    await revalidate_listing(db, listing)


async def _publish_making_video(db: AsyncSession, listing: Listing, profile: ArtisanProfile) -> None:
    from app.modules.auth.models import Consent
    from app.modules.media.service import publish_copy

    consent = (await db.execute(select(Consent).where(Consent.user_id == profile.user_id, Consent.consent_type == "public_video",
                                                      Consent.revoked_at.is_(None)))).first()
    if not consent:
        return
    vids = await listing_media(db, listing.id, ("making_video",))
    if vids:
        await publish_copy(db, vids[-1][1])


async def revoke(db: AsyncSession, listing: Listing, reason: str, actor: uuid.UUID | None = None) -> None:
    from app.core.revalidate import revalidate_listing
    from app.modules.notifications.service import notify

    listing.verification_status = "revoked"
    units = (await db.execute(select(KaruId).where(KaruId.listing_id == listing.id))).scalars().all()
    for k in units:
        db.add(KaruIdEvent(karu_id=k.id, event="revoked", actor_user_id=actor, data={"reason": reason}))
        if k.status == "available":
            k.verification_run_id = None
    profile = await db.get(ArtisanProfile, listing.artisan_id)
    title = next(iter((listing.title or {}).values()), "")
    await notify(db, profile.user_id, "verification_not_verified", {"title": title},
                 link=f"/sell/products/{listing.id}?tab=verification")
    await evaluate_passport(db, profile)
    await revalidate_listing(db, listing)


@on_failure("verification.run")
async def verification_failed(db: AsyncSession, job) -> None:
    run = await db.get(VerificationRun, uuid.UUID(job.payload["run_id"]))
    if run is None:
        return
    run.status, run.error = "failed", job.error
    listing = await db.get(Listing, run.listing_id)
    if listing and listing.verification_status == "checking" and listing.current_verification_run_id == run.id:
        prev = (await db.execute(select(VerificationRun).where(VerificationRun.listing_id == listing.id,
                                                               VerificationRun.status == "completed")
                                 .order_by(desc(VerificationRun.completed_at)).limit(1))).scalar_one_or_none()
        listing.verification_status = (prev.verdict if prev and prev.listing_version == listing.version else "not_verified")


@periodic("verification.rescans", every_s=6 * 3600)
async def periodic_rescans(db: AsyncSession) -> None:
    """Anti-counterfeit re-scan of verified listings every N days, and re-queue deferred web checks."""
    cfg = await get_config(db, "verification.v1")
    cutoff = utcnow() - timedelta(days=cfg["periodic_rescan_days"])
    verified = (await db.execute(select(Listing).where(Listing.verification_status == "verified",
                                                       Listing.status == "published"))).scalars().all()
    for li in verified:
        last = (await db.execute(select(VerificationRun).where(VerificationRun.listing_id == li.id)
                                 .order_by(desc(VerificationRun.created_at)).limit(1))).scalar_one_or_none()
        if last is None or last.status not in ("queued", "running") and (
                last.created_at < cutoff or (last.deferred_checks and last.created_at < utcnow() - timedelta(hours=20))):
            await start_run(db, li, "periodic")


async def rescore(db: AsyncSession, run: VerificationRun, cfg: dict) -> dict:
    """S06 'Re-score with current config': stored layer scores, no new AI calls."""
    decision = scoring.decide(run.l1_score or 0, run.l2_score, run.l3_score, hard_fail=run.hard_fail, cfg=cfg)
    return {"run_id": str(run.id), "old": {"score": run.karu_score, "verdict": run.verdict},
            "new": {"score": decision.karu_score, "verdict": decision.verdict}}
