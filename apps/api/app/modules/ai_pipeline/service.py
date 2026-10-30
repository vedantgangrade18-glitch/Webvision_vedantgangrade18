"""Snap + Speak pipeline (Part 2 §6): photos + voice note → reviewed draft listing.

Steps (job progress): transcribe → understand (structured extraction) → write
(title/description in source language + English + Hindi) → draft ready. Partial results
stream to the wait screen via `job.result["preview"]`. Then, in the background:
enhance photos (non-generative) + AI catalogue shots (Gemini), and market prices.
Extraction failing twice falls back to the manual form (F2 edge case); the artisan
always reviews before publishing. Originals are kept for verification and proof; AI shots
go in the gallery and can be removed by the artisan.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import imaging
from app.core.db import utcnow
from app.core.i18n import LANGUAGE_NAMES_EN
from app.core.jobs import enqueue, handler, on_failure, set_progress
from app.core.storage import get_storage
from app.modules.artisans.models import ArtisanProfile
from app.modules.artisans.service import place_of
from app.modules.catalog import attributes
from app.modules.catalog.models import AiExtraction, Category, Craft, Listing, ListingMedia
from app.modules.catalog.service import all_categories, listing_media, refresh_search
from app.modules.media.models import Media
from app.providers.imagegen import get_imagegen
from app.providers.llm import get_llm, rule_based_extract
from app.providers.stt import get_stt

logger = logging.getLogger(__name__)

# Attribute fields come from the category specs (catalog/reference.py). The LLM only fills values;
# missing fields and notes are computed from the specs, never taken from the model.
_ATTR_SCHEMA, _ATTR_KEYS = attributes.llm_schema()
EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "category_slug": {"type": "string"},
        "craft_slug": {"type": "string"},
        "attributes": _ATTR_SCHEMA,
        "price_inr": {"type": "number"},
        "quantity_mentioned": {"type": "integer"},
        "field_confidence": {"type": "object", "properties": {
            k: {"type": "number"} for k in ("category_slug", "price_inr", *_ATTR_KEYS)}},
    },
    "required": ["attributes", "field_confidence"],
}

DESCRIBE_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "object", "properties": {"source": {"type": "string"}, "en": {"type": "string"}, "hi": {"type": "string"}},
                  "required": ["source", "en", "hi"]},
        "description": {"type": "object", "properties": {"source": {"type": "string"}, "en": {"type": "string"}, "hi": {"type": "string"}},
                        "required": ["source", "en", "hi"]},
        "tags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["title", "description", "tags"],
}

WRITING_RULES = (
    "Rules: warm and factual, 60–120 words for the description, no invented claims. Use ONLY facts from the transcript "
    "and what is visible in the photos. Never claim 'GI certified', 'organic', 'pure silk', 'natural dye' or any origin "
    "detail unless the artisan said it. Do not mention prices. Titles under 70 characters. Tags: 3–8 short lowercase "
    "English keywords."
)


async def _photos_for_llm(db: AsyncSession, listing: Listing, limit: int = 3) -> list[tuple[bytes, str]]:
    rows = await listing_media(db, listing.id, ("photo",))
    out = []
    st = get_storage()
    for _, m in rows[:limit]:
        data = await st.get_private(m.storage_key)
        img = await asyncio.to_thread(imaging.load_image, data)
        out.append((await asyncio.to_thread(imaging.compress_for_llm, img), "image/jpeg"))
    return out


async def extract(db: AsyncSession, listing: Listing, transcript: str, photos, category_slugs: list[str],
                  crafts: list[Craft]) -> dict:
    llm = get_llm()
    craft_list = [{"slug": c.slug, "name": (c.name or {}).get("en"), "category": c.category_slug} for c in crafts]
    prompt = (
        "You help Indian artisans list handmade products. From the artisan's voice-note transcript (in "
        f"{LANGUAGE_NAMES_EN.get(listing.source_lang, listing.source_lang)}) and the product photos, extract structured "
        "listing data. Only use facts the artisan said or that are clearly visible. Prices are in Indian rupees; convert "
        "number words to digits (e.g. 'अठारह सौ' → 1800). If something is not stated or visible, omit the key "
        "rather than guessing. field_confidence values are 0–1.\n"
        f"Allowed category_slug values: {json.dumps(category_slugs)}.\n"
        f"Known crafts (craft_slug only if clearly this craft): {json.dumps(craft_list, ensure_ascii=False)}.\n"
        f"TRANSCRIPT:\n{transcript or '(no voice note — use photos only; price will be asked separately)'}"
    )
    extract_schema = EXTRACT_SCHEMA
    if category_slugs:
        import copy
        extract_schema = copy.deepcopy(EXTRACT_SCHEMA)
        extract_schema["properties"]["category_slug"]["enum"] = category_slugs
    last_exc: Exception | None = None
    for attempt in range(2):
        try:
            result = await llm.generate_json(prompt, schema=extract_schema, purpose="extract", images=photos,
                                             temperature=0.1 + attempt * 0.2, listing_id=listing.id,
                                             fake_context={"transcript": transcript, "category_slugs": category_slugs})
            if result.get("category_slug") not in category_slugs:
                result["category_slug"] = None
            return result
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
    raise ExtractionFailed(str(last_exc))


class ExtractionFailed(Exception):
    pass


async def describe(listing: Listing, transcript: str, photos, extracted: dict, *, craft_name: str | None, place: str,
                   maker: str, variant: int = 0, only_field: str | None = None) -> dict:
    llm = get_llm()
    src = listing.source_lang
    prompt = (
        f"Write a marketplace title and description for this handmade product in three languages: the artisan's language "
        f"('{src}', {LANGUAGE_NAMES_EN.get(src, src)}) as `source`, English as `en`, Hindi as `hi`. {WRITING_RULES}\n"
        f"Maker: {maker}. Place: {place}. Craft: {craft_name or 'unknown'}.\n"
        f"Structured facts: {json.dumps(extracted.get('attributes', {}), ensure_ascii=False)}\n"
        f"Artisan's words: {transcript or '(none)'}"
    )
    if only_field:
        prompt += f"\nWrite a fresh alternative {only_field} (variation #{variant}); keep the other fields short."
    res = await llm.generate_json(
        prompt, schema=DESCRIBE_SCHEMA, purpose="describe" if not only_field else "regenerate_field", images=photos,
        temperature=0.4 + 0.15 * min(variant, 4), listing_id=listing.id,
        fake_context={"attributes": extracted.get("attributes", {}), "category_slug": extracted.get("category_slug"),
                      "craft_name": craft_name, "place": place, "transcript": transcript, "source_lang": src,
                      "variant": variant, "field": only_field},
    )
    # Normalise {source, en, hi} → {src_lang: …, en: …, hi: …}
    out = {}
    for field in ("title", "description"):
        vals = res.get(field) or {}
        if not vals:
            continue
        mapped = {k: v for k, v in vals.items() if k in ("en", "hi") and v}
        if vals.get("source"):
            mapped[src] = vals["source"]
        elif vals.get(src):
            mapped[src] = vals[src]
        out[field] = mapped
    if res.get("tags"):
        out["tags"] = [str(t).lower()[:32] for t in res["tags"]][:10]
    if res.get("attributes"):
        out["attributes"] = res["attributes"]
    return out


async def enhance_photos(db: AsyncSession, listing: Listing) -> int:
    """Non-generative enhancement; originals stay private and are used for verification."""
    st = get_storage()
    rows = await listing_media(db, listing.id, ("photo", "enhanced_photo"))
    have = {lm.source_media_id for lm, _ in rows if lm.role == "enhanced_photo"}
    count = 0
    for lm, m in rows:
        if lm.role != "photo" or m.id in have:
            continue
        data = await st.get_private(m.storage_key)
        img = await asyncio.to_thread(imaging.load_image, data)
        enhanced = await asyncio.to_thread(imaging.enhance, img)
        derived = Media(owner_user_id=m.owner_user_id, kind="derived_image", mime="image/jpeg", storage_key="pending",
                        status="ready", created_at=utcnow())
        db.add(derived)
        await db.flush()
        derived.storage_key = f"derived/{derived.id}.jpg"
        await st.put_private(derived.storage_key, imaging.encode(enhanced, "JPEG", 90), "image/jpeg")
        vars_ = await asyncio.to_thread(imaging.variants, enhanced)
        keys = {}
        for name, blob in vars_.items():
            key = f"public/{derived.id}/{name}"
            await st.put_public(key, blob, "image/webp" if name.endswith(".webp") else "image/jpeg")
            keys[name] = key
        derived.variants = keys
        derived.public_key = keys.get("800_4x5.jpg")
        derived.width, derived.height = enhanced.size
        derived.phash = m.phash  # derived from the same photo
        derived.embedding = m.embedding
        db.add(ListingMedia(listing_id=listing.id, media_id=derived.id, role="enhanced_photo", position=lm.position,
                            is_primary=lm.is_primary, source_media_id=m.id))
        count += 1
    return count

SHOT_GROUPS = {
    "pottery-terracotta": "object",
    "woodcraft": "object",
    "metal-brass": "object",
    "bamboo-cane": "object",
    "toys": "object",
    "other": "object",
    "sarees": "textile",
    "dupattas-stoles": "textile",
    "kurtas-fabric": "textile",
    "home-textiles": "home",
    "jewellery": "jewel",
    "paintings": "art",
    "leather": "leather",
}

# Art direction per shot. Photography language (lens, light, surface, composition) is what lifts
# Nano Banana output from "AI-looking" to catalogue grade; keep each line concrete and visual.
_WHITE = ("seamless pure-white (#FFFFFF) studio sweep, large overhead softbox key light from upper-left, white bounce "
          "fill from the right, subtle contact shadow under the product, 85mm lens at f/8, everything tack-sharp")
_MACRO = ("100mm macro lens, focus-stacked so the whole detail is sharp, raking side light at a low angle to reveal "
          "texture and relief, frame filled edge to edge by the product surface, no background visible")
_HOME = ("warm, uncluttered Indian home styled like a premium décor catalogue: soft golden-hour window light from the "
         "side, gentle shadows, shallow depth of field (50mm, f/2.8) with the product in sharp focus on a rule-of-thirds "
         "point; tasteful props only (handloom jute runner, teak wood, brass, a few marigolds or a green plant), muted "
         "earthy palette so the product is the hero")

SHOTS: dict[str, list[tuple[str, str]]] = {
    "object": [
        ("hero", f"Hero packshot: three-quarter front view, slightly above eye level, product fills ~80% of the frame, "
                 f"centred. {_WHITE}."),
        ("lifestyle", f"Lifestyle: the product placed naturally on a wooden shelf, console or dining table. {_HOME}."),
        ("detail", f"Detail close-up of the most characteristic surface — glaze, carving, engraving, weave or tool marks. "
                   f"{_MACRO}."),
        ("scale", "Scale shot: the product gently held in an Indian person's hand (hand and wrist only, natural skin, "
                  "clean short nails) or beside an everyday chai cup, so its true size is obvious; soft daylight, "
                  "neutral light-grey backdrop, 50mm f/4."),
        ("angle", f"Alternate angle: clean side profile or top-down view showing the form from a new direction. {_WHITE}."),
    ],
    "textile": [
        ("hero", f"Hero packshot: neatly folded with crisp edges, border and pallu motif visible on top, product fills "
                 f"~80% of the frame. {_WHITE}."),
        ("worn", "On-model: elegantly draped/worn by an Indian model in a natural, graceful pose, cropped at the "
                 "shoulders or showing the full drape; light-grey seamless studio backdrop, large soft key light with "
                 "gentle rim light, 85mm f/4, fabric falls in natural folds that show its sheen and weight."),
        ("detail", f"Detail close-up of the weave, embroidery or printed motif, individual threads visible. {_MACRO}."),
        ("spread", "Flat lay from directly overhead: fully spread out to show the complete pattern, border and pallu, "
                   "smoothed with natural soft folds at the edges, on a light warm-grey linen surface, even shadowless "
                   "diffused light, true-to-life colour."),
        ("lifestyle", f"Festive lifestyle: styled for a celebration — draped over a carved wooden chair or folded on a "
                      f"brass tray with diyas and marigolds, warm bokeh lights in the background. {_HOME}."),
    ],
    "home": [
        ("hero", f"Hero packshot: neatly folded stack with edges aligned, pattern visible, fills ~80% of the frame. {_WHITE}."),
        ("lifestyle", f"Lifestyle: in use on a made bed, sofa or dining table in a bright, airy room. {_HOME}."),
        ("detail", f"Detail close-up of the weave, block print or embroidery. {_MACRO}."),
        ("spread", "Flat lay from directly overhead showing the full pattern edge to edge, on a light warm-grey surface, "
                   "even diffused light, true-to-life colour."),
        ("scale", f"In context on furniture so the real size reads instantly (a cushion on an armchair, a runner on a "
                  f"table). {_HOME}."),
    ],
    "jewel": [
        ("hero", f"Hero packshot: product fills ~75% of the frame, slight angle to catch highlights on metal and stones, "
                 f"controlled specular reflections, no blown-out hotspots. {_WHITE}."),
        ("worn", "On-model: close crop of an Indian model's neck, ear or wrist wearing the piece, natural skin texture, "
                 "soft beauty lighting with a large diffused key, neutral warm backdrop, 100mm f/4, jewellery in "
                 "razor-sharp focus."),
        ("detail", f"Macro of the craftsmanship — filigree, stone setting, enamel or engraving. {_MACRO}."),
        ("scale", "Scale shot: resting in an open palm (hand only), soft daylight, neutral light-grey backdrop, 85mm f/4."),
        ("lifestyle", "Gift mood: arranged on rich silk fabric or an open velvet jewellery box beside a brass tray and a "
                      "few rose petals, warm soft light, shallow depth of field, luxurious but uncluttered."),
    ],
    "art": [
        ("hero", "Hero: perfectly straight-on, square to the camera with no keystone distortion, even shadowless "
                 "gallery lighting from two diffused sources at 45°, white surround, colours true to the original."),
        ("lifestyle", f"Lifestyle: hanging at eye level on a plain warm-white wall above a sofa or sideboard, correct "
                      f"real-world scale. {_HOME}."),
        ("detail", f"Close-up of the brushwork, linework or paper/canvas texture. {_MACRO}."),
        ("angle", "30° angled view showing the edge, frame and depth of the piece, soft gallery light, white surround."),
        ("scale", f"Scale: on a wall next to a chair or a person seen from behind, so the size is obvious. {_HOME}."),
    ],
    "leather": [
        ("hero", f"Hero packshot: three-quarter view, shape fully presented (stuffed if a bag), fills ~80% of the frame. "
                 f"{_WHITE}."),
        ("worn", "In use: carried or worn by an Indian person (product in focus, face out of frame), natural outdoor "
                 "daylight in a clean urban or courtyard setting, 85mm f/2.8 with soft background blur."),
        ("detail", f"Detail of the stitching, tooling, edge finish and grain. {_MACRO}."),
        ("angle", f"Opened up to show the inside, lining and compartments. {_WHITE}."),
        ("scale", "Scale shot: held in a hand (hand and wrist only), soft daylight, neutral light-grey backdrop, 50mm f/4."),
    ],
}

# Retry instructions for shots that need a person (often safety-blocked); same role, no people.
SHOT_FALLBACKS = {
    "worn": "Styled on a neutral fabric mannequin/bust (no person), light-grey studio backdrop, soft key light, 85mm f/4.",
    "scale": "Placed beside familiar everyday objects (a chai cup, a book) on a light wood table so the size is obvious, "
             "soft daylight, 50mm f/4. No people.",
}

SHOT_PROMPT_PREFIX = (
    "You are a world-class product photographer shooting a premium e-commerce catalogue for handmade Indian crafts. "
    "Create ONE photorealistic photograph of the product in the reference photo(s). Image 1 is the main reference; "
    "any others show the same product from other angles.\n"
    "PRODUCT FIDELITY (most important): the product must be exactly the same object — identical shape, proportions, "
    "colours, pattern, motif count and placement, glaze, texture and every handmade irregularity. Do not redesign, "
    "clean up, add or remove anything on the product. Show exactly one product."
)

SHOT_PROMPT_SUFFIX = (
    "Look and finish: high-end commercial photography, true-to-life colour, natural contrast, crisp micro-detail, "
    "realistic materials and shadows. Avoid: CGI or plastic look, oversaturation, harsh flash, distorted perspective, "
    "cluttered props competing with the product, duplicated products, any text, logos, labels or watermarks."
)


def _product_context(listing: Listing, craft_name: str | None, place: str) -> list[str]:
    title = listing.title or {}
    desc = listing.description or {}
    attrs = listing.attributes or {}
    lines = []
    if t := title.get("en") or title.get(listing.source_lang):
        lines.append(f"Product: {t}")
    if craft_name:
        lines.append(f"Craft: {craft_name}" + (f", made in {place}" if place else ""))
    for key, label in (("material", "Material"), ("technique", "Technique"), ("finish", "Finish"), ("dye", "Dye")):
        if attrs.get(key):
            lines.append(f"{label}: {attrs[key]}")
    if colours := attrs.get("colour"):
        lines.append(f"Colours (keep exact): {', '.join(map(str, colours)) if isinstance(colours, list) else colours}")
    dims = attrs.get("dimensions")
    if isinstance(dims, dict) and (d := ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in dims.items() if v)):
        lines.append(f"Real size: {d} — render at this true scale")
    if d := (desc.get("en") or "")[:220]:
        lines.append(f"About: {d}")
    return lines


def _shot_prompt(instruction: str, context: list[str]) -> str:
    parts = [SHOT_PROMPT_PREFIX]
    if context:
        parts.append("Product facts:\n" + "\n".join(f"- {c}" for c in context))
    parts += [f"THIS SHOT: {instruction}", SHOT_PROMPT_SUFFIX]
    return "\n\n".join(parts)


async def generate_shots(db: AsyncSession, listing: Listing, job=None) -> int:
    """Generate up to 5 marketplace-style AI catalogue images from real photos.

    API calls run concurrently (bounded); each finished shot is saved and committed as it lands so the
    review screen fills in progressively. A failed shot is retried once (people shots retry without people).
    """
    rows = await listing_media(db, listing.id, ("photo",))
    if not rows:
        return 0
    rows.sort(key=lambda r: (not r[0].is_primary, r[0].position))
    primary_orig = rows[0][1]

    # Originals (not the enhanced copies: gray-world balancing can shift true product colours), high-res.
    st = get_storage()
    photo_bytes: list[bytes] = []
    for _, m in rows[:3]:
        img = await asyncio.to_thread(imaging.load_image, await st.get_private(m.storage_key))
        photo_bytes.append(await asyncio.to_thread(imaging.compress_for_llm, img, 2048, 92))

    cat_slug = "other"
    if listing.category_id and (cat := await db.get(Category, listing.category_id)):
        cat_slug = cat.slug
    shot_list = SHOTS.get(SHOT_GROUPS.get(cat_slug, "object"), SHOTS["object"])

    craft = await db.get(Craft, listing.craft_id) if listing.craft_id else None
    profile = await db.get(ArtisanProfile, listing.artisan_id) if listing.artisan_id else None
    context = _product_context(listing, (craft.name or {}).get("en") if craft else None,
                               place_of(profile) if profile else "")

    existing = {lm.role for lm, _ in await listing_media(db, listing.id) if (lm.role or "").startswith("ai_")}
    todo = [(i, shot, instr) for i, (shot, instr) in enumerate(shot_list) if f"ai_{shot}" not in existing]
    if not todo:
        return 0
    imagegen = get_imagegen()
    sem = asyncio.Semaphore(3)  # ponytail: fixed concurrency; make it a setting if the Vertex quota changes

    async def render(i: int, shot: str, instruction: str):
        for n, instr in enumerate((instruction, SHOT_FALLBACKS.get(shot, instruction))):
            try:
                async with sem:
                    return i, shot, await imagegen.edit(_shot_prompt(instr, context), photo_bytes, aspect_ratio="4:5",
                                                        purpose="ai_image", listing_id=listing.id)
            except Exception as exc:  # noqa: BLE001
                logger.warning("ai shot %s attempt %d failed for listing %s: %s", shot, n + 1, listing.id, exc)
        return i, shot, None

    count, done, total = 0, 0, len(todo)
    # Renders run concurrently, but all DB work happens here, one shot at a time, on the single session.
    for fut in asyncio.as_completed([render(*t) for t in todo]):
        i, shot, ai_bytes = await fut
        done += 1
        if ai_bytes is not None:
            try:
                await _save_shot(db, listing, primary_orig, f"ai_{shot}", i, ai_bytes)
                count += 1
            except Exception as exc:  # noqa: BLE001
                await db.rollback()
                logger.warning("saving ai shot %s failed for listing %s: %s", shot, listing.id, exc)
        if job:
            await set_progress(db, job, 5 + int(done / total * 95), f"shot_{shot}")
            await db.commit()
    return count


async def _save_shot(db: AsyncSession, listing: Listing, primary_orig: Media, role: str, position: int,
                     ai_bytes: bytes) -> None:
    st = get_storage()
    ai_img = await asyncio.to_thread(imaging.load_image, ai_bytes)
    derived = Media(owner_user_id=primary_orig.owner_user_id, kind="ai_image", mime="image/jpeg",
                    storage_key="pending", status="ready", created_at=utcnow())
    db.add(derived)
    await db.flush()
    derived.storage_key = f"derived/{derived.id}.jpg"
    await st.put_private(derived.storage_key, imaging.encode(ai_img, "JPEG", 92), "image/jpeg")
    keys = {}
    for name, blob in (await asyncio.to_thread(imaging.variants, ai_img)).items():
        key = f"public/{derived.id}/{name}"
        await st.put_public(key, blob, "image/webp" if name.endswith(".webp") else "image/jpeg")
        keys[name] = key
    derived.variants = keys
    derived.public_key = keys.get("800_4x5.jpg")
    derived.width, derived.height = ai_img.size
    db.add(ListingMedia(listing_id=listing.id, media_id=derived.id, role=role, position=position,
                        source_media_id=primary_orig.id))
    await db.commit()


@handler("ai.generate_shots", queue="ai", max_attempts=2, timeout_s=600)
async def generate_shots_job(db: AsyncSession, job) -> dict:
    listing = await db.get(Listing, uuid.UUID(job.ref_id))
    if listing is None:
        return {"skipped": True}
    # Non-generative clean-up first (fast, idempotent); the progress bump makes the review screen refetch.
    await enhance_photos(db, listing)
    await set_progress(db, job, 5, "enhancing_photos")
    count = await generate_shots(db, listing, job=job)
    return {"listing_id": str(listing.id), "shots_generated": count}


async def _context(db: AsyncSession, listing: Listing) -> tuple[ArtisanProfile, list[str], list[Craft]]:
    profile = await db.get(ArtisanProfile, listing.artisan_id)
    cats = [c.slug for c in await all_categories(db)]
    crafts = list((await db.execute(select(Craft))).scalars())
    return profile, cats, crafts


@handler("ai.process_listing", queue="ai", max_attempts=2, timeout_s=300)
async def process_listing(db: AsyncSession, job) -> dict:
    started = time.perf_counter()
    listing = await db.get(Listing, uuid.UUID(job.ref_id))
    if listing is None:
        return {"skipped": True}
    profile, cat_slugs, crafts = await _context(db, listing)
    payload = job.payload or {}

    # 1. Transcribe
    await set_progress(db, job, 10, "listening")
    transcript_text, transcript = "", None
    voice = await listing_media(db, listing.id, ("voice_note",))
    if voice:
        m = voice[-1][1]
        if m.transcript and m.transcript.get("text"):
            transcript = m.transcript
        else:
            try:
                audio = await get_storage().get_private(m.storage_key)
                tr = await get_stt().transcribe(audio, m.mime, listing.source_lang, duration_s=m.duration_s,
                                                client_transcript=payload.get("client_transcript"), listing_id=listing.id)
                transcript = {"lang": tr.language, "text": tr.text, "confidence": tr.confidence, "provider": tr.provider,
                              "segments": tr.segments}
            except Exception as exc:
                logger.warning("Audio transcription failed for %s: %s; falling back to client transcript", listing.id, exc)
                c_text = (payload.get("client_transcript") or "").strip()
                transcript = {"lang": listing.source_lang, "text": c_text, "confidence": 0.5 if c_text else 0.0,
                              "provider": "browser" if c_text else "fallback", "segments": []}
            m.transcript = transcript
        transcript_text = transcript.get("text", "")
    elif payload.get("client_transcript"):
        transcript_text = payload["client_transcript"]
        transcript = {"lang": listing.source_lang, "text": transcript_text, "confidence": 0.6, "provider": "browser"}

    # Partial results ride on job.result so the wait screen can show them as they land (SSE pushes changes).
    preview = {"transcript": transcript_text}
    job.result = {"preview": preview}

    # 2. Understand
    await set_progress(db, job, 35, "understanding")
    photos = await _photos_for_llm(db, listing)
    fallback = False
    try:
        extracted = await extract(db, listing, transcript_text, photos, cat_slugs, crafts)
    except ExtractionFailed:
        extracted = rule_based_extract(transcript_text, cat_slugs)
        fallback = True
    cat = None
    if extracted.get("category_slug"):
        cat = (await db.execute(select(Category).where(Category.slug == extracted["category_slug"]))).scalar_one_or_none()
        listing.category_id = cat.id if cat else listing.category_id
    if cat is None and listing.category_id:
        cat = await db.get(Category, listing.category_id)
    craft = None
    if extracted.get("craft_slug"):
        craft = next((c for c in crafts if c.slug == extracted["craft_slug"]), None)
    if craft is None and profile and profile.crafts:
        craft = next((c for c in crafts if c.slug in profile.crafts), None)
    if craft:
        listing.craft_id = craft.id
    listing.attributes = attributes.normalize({**(extracted.get("attributes") or {}), **(listing.attributes or {})})
    if extracted.get("price_inr") and listing.price_inr is None:
        listing.price_inr = Decimal(str(round(float(extracted["price_inr"]), 2)))
    listing.field_confidence = extracted.get("field_confidence") or {}
    listing.missing_fields = attributes.missing_fields(cat.attribute_schema if cat else None, listing.attributes,
                                                       price=listing.price_inr, has_category=cat is not None)
    listing.notes_for_artisan = attributes.notes_for_artisan(price=listing.price_inr)
    preview = {**preview, "category_slug": extracted.get("category_slug"),
               "price_inr": float(listing.price_inr) if listing.price_inr is not None else None,
               "material": (listing.attributes or {}).get("material")}
    job.result = {"preview": preview}
    await db.commit()

    # 3. Write
    await set_progress(db, job, 65, "writing")
    place = place_of(profile) if profile else ""
    try:
        written = await describe(listing, transcript_text, photos, extracted,
                                 craft_name=(craft.name or {}).get("en") if craft else None, place=place,
                                 maker=profile.public_name if profile else "")
    except Exception:  # noqa: BLE001
        written = {}
        fallback = True
    if written.get("title"):
        listing.title = {**written["title"], **{k: v for k, v in (listing.title or {}).items() if v}}
    if written.get("description"):
        listing.description = {**written["description"], **{k: v for k, v in (listing.description or {}).items() if v}}
    if written.get("tags"):
        listing.tags = written["tags"]

    c_name = (craft.name or {}).get("en") if craft else (cat.name if cat else "Handmade Craft")
    c_name = c_name or "Handmade Indian Craft"
    if not listing.title or not any(listing.title.values()):
        listing.title = {
            "en": f"Handcrafted {c_name}",
            "hi": f"हस्तनिर्मित {c_name}",
            listing.source_lang: f"Handcrafted {c_name}",
        }
    if not listing.description or not any(listing.description.values()):
        mat = (listing.attributes or {}).get("material") or "authentic materials"
        tech = (listing.attributes or {}).get("technique") or "traditional craftsmanship"
        desc_en = f"Authentic handcrafted {c_name} made with {mat} using {tech}. Checked by Karu verification."
        listing.description = {
            "en": desc_en,
            "hi": f"पारंपरिक भारतीय हस्तशिल्प ({c_name}), {mat} और {tech} से निर्मित।",
            listing.source_lang: desc_en,
        }
    if not listing.tags:
        listing.tags = ["handmade", "craft", "authentic", "karu"]
    title = listing.title or {}
    job.result = {"preview": {**preview, "title": title.get(listing.source_lang) or title.get("en")}}
    await db.commit()

    # Photo enhancement and market prices are slow and not needed to review the text, so they run as
    # background jobs (ai.generate_shots, pricing.refresh_listing) after the draft is handed over.
    primary = await listing_media(db, listing.id, ("photo",))
    if primary:
        prim = next((m for lm, m in primary if lm.is_primary), primary[0][1])
        listing.image_embedding = prim.embedding
    await refresh_search(db, listing)
    if listing.status == "processing":
        listing.status = "draft"
    db.add(AiExtraction(
        listing_id=listing.id,
        input_media_ids=[str(m.id) for _, m in await listing_media(db, listing.id, ("photo", "voice_note"))],
        transcript=transcript, extracted=extracted, field_confidence=extracted.get("field_confidence"),
        model_versions={"llm": get_llm().name, "stt": transcript.get("provider") if transcript else None},
        duration_ms=int((time.perf_counter() - started) * 1000), status="fallback" if fallback else "completed",
    ))
    await db.commit()
    owner = profile.user_id if profile else getattr(job, "owner_user_id", None)
    await enqueue(db, "ai.generate_shots", ref_type="listing", ref_id=str(listing.id), owner_user_id=owner)
    await enqueue(db, "pricing.refresh_listing", ref_type="listing", ref_id=str(listing.id), owner_user_id=owner)
    await db.commit()
    return {"listing_id": str(listing.id), "fallback": fallback}


@on_failure("ai.process_listing")
async def process_listing_failed(db: AsyncSession, job) -> None:
    listing = await db.get(Listing, uuid.UUID(job.ref_id))
    if listing and listing.status == "processing":
        listing.status = "draft"  # manual form with mic buttons (F2 edge case)
        listing.notes_for_artisan = ["manual_form"]


@handler("ai.regenerate", queue="ai", max_attempts=1, timeout_s=120)
async def regenerate(db: AsyncSession, job) -> dict:
    listing = await db.get(Listing, uuid.UUID(job.ref_id))
    if listing is None:
        return {"skipped": True}
    field = job.payload["field"]
    variant = int(job.payload.get("variant", 1))
    profile, cat_slugs, crafts = await _context(db, listing)
    ext = (await db.execute(select(AiExtraction).where(AiExtraction.listing_id == listing.id)
                            .order_by(AiExtraction.created_at.desc()).limit(1))).scalar_one_or_none()
    transcript = ((ext.transcript or {}).get("text") if ext else "") or ""
    craft = await db.get(Craft, listing.craft_id) if listing.craft_id else None
    category = await db.get(Category, listing.category_id) if listing.category_id else None
    photos = await _photos_for_llm(db, listing, limit=2)
    extracted = {"attributes": listing.attributes, "category_slug": category.slug if category else None}
    await set_progress(db, job, 30, f"regenerating_{field}")
    if field == "attributes":
        fresh = await extract(db, listing, transcript, photos, cat_slugs, crafts)
        listing.attributes = attributes.normalize(fresh.get("attributes")) or listing.attributes
        listing.field_confidence = fresh.get("field_confidence") or listing.field_confidence
        listing.missing_fields = attributes.missing_fields(category.attribute_schema if category else None, listing.attributes,
                                                           price=listing.price_inr, has_category=category is not None)
    else:
        written = await describe(listing, transcript, photos, extracted, craft_name=(craft.name or {}).get("en") if craft else None,
                                 place=place_of(profile), maker=profile.public_name, variant=variant,
                                 only_field=None if field == "all" else field)
        if field in ("title", "all") and written.get("title"):
            listing.title = written["title"]
        if field in ("description", "all") and written.get("description"):
            listing.description = written["description"]
        if field in ("tags", "all") and written.get("tags"):
            listing.tags = written["tags"]
    await refresh_search(db, listing)
    await db.commit()
    return {"field": field}


TRANSLATE_SCHEMA = {"type": "object", "properties": {"title": {"type": "string"}, "description": {"type": "string"}},
                    "required": ["title", "description"]}


@handler("ai.translate", queue="ai", max_attempts=2, timeout_s=120)
async def translate_listing(db: AsyncSession, job) -> dict:
    """Buyer-locale translation on first view, cached on the listing (Part 2 §6.4)."""
    listing = await db.get(Listing, uuid.UUID(job.ref_id))
    target = job.payload.get("locale")
    llm = get_llm()
    if listing is None or not target or target in (listing.description or {}) or llm.name == "fake":
        return {"skipped": True}
    src = listing.source_lang if listing.source_lang in (listing.description or {}) else "en"
    res = await llm.generate_json(
        f"Translate this handmade-product title and description from {LANGUAGE_NAMES_EN.get(src, src)} into "
        f"{LANGUAGE_NAMES_EN.get(target, target)}. Keep craft names and place names as they are. Do not add claims.\n"
        f"TITLE: {(listing.title or {}).get(src, '')}\nDESCRIPTION: {(listing.description or {}).get(src, '')}",
        schema=TRANSLATE_SCHEMA, purpose="translate", temperature=0.2, listing_id=listing.id,
        fake_context={"text": (listing.description or {}).get(src, "")},
    )
    if res.get("title"):
        listing.title = {**listing.title, target: res["title"]}
    if res.get("description"):
        listing.description = {**listing.description, target: res["description"]}
    await refresh_search(db, listing)
    await db.commit()
    return {"locale": target}
