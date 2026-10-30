from __future__ import annotations

import asyncio
import hashlib
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import imaging, video
from app.core.errors import AppError, bad_request
from app.core.jobs import handler
from app.core.storage import get_storage
from app.modules.media.models import Media

MAX_BYTES = {"photo": 15 * 1024 * 1024, "voice": 12 * 1024 * 1024, "video": 300 * 1024 * 1024,
             "document": 10 * 1024 * 1024}
MAX_DURATION = {"voice": 150, "video": 300}
MIN_VIDEO_S = 20


def storage_key(media: Media, ext: str = "bin") -> str:
    return f"{media.kind}/{media.created_at:%Y/%m}/{media.id}.{ext}"


async def finalize(db: AsyncSession, media: Media, client_duration: float | None = None) -> Media:
    """Validate magic bytes and extract metadata; photos are fully processed inline (fast),
    voice/video get their slower processing in the media worker."""
    storage = get_storage()
    data = await storage.get_private(media.storage_key)
    sniffed = imaging.sniff_mime(data)
    if not imaging.kind_accepts(media.kind, sniffed):
        media.status, media.error = "failed", f"unsupported_type:{sniffed}"
        await storage.delete_private(media.storage_key)
        await db.commit()
        raise bad_request("unsupported_media_type", sniffed=sniffed)
    media.bytes = len(data)
    media.sha256 = hashlib.sha256(data).hexdigest()
    if media.kind == "photo":
        clean, derived = await asyncio.to_thread(_process_photo_sync, media, data)
        await storage.put_private(media.storage_key, clean, "image/jpeg")
        for name, blob in derived.items():
            key = f"public/{media.id}/{name}"
            await storage.put_public(key, blob, "image/webp" if name.endswith(".webp") else "image/jpeg")
            media.variants = {**(media.variants or {}), name: key}
        media.public_key = (media.variants or {}).get("800_4x5.jpg") or (media.variants or {}).get("400_4x5.jpg")
        media.mime = "image/jpeg"
        media.status = "ready"
    else:
        media.mime = sniffed if media.kind == "video" or not sniffed.startswith("video/") else sniffed.replace("video/", "audio/")
        duration = await video.probe_duration(data) or client_duration
        media.duration_s = duration
        limit = MAX_DURATION.get(media.kind)
        if duration and limit and duration > limit + 5:
            media.status, media.error = "failed", "too_long"
            await db.commit()
            raise bad_request("media_too_long", max_s=limit)
        if media.kind == "video" and duration and duration < MIN_VIDEO_S - 2:
            media.status, media.error = "failed", "too_short"
            await db.commit()
            raise bad_request("video_too_short", min_s=MIN_VIDEO_S)
        media.status = "ready"
        if media.kind == "video":
            from app.core.jobs import enqueue

            await enqueue(db, "media.video_poster", ref_type="media", ref_id=str(media.id), payload={"id": str(media.id)})
    return media


def _process_photo_sync(media: Media, data: bytes) -> tuple[bytes, dict[str, bytes]]:
    img = imaging.load_image(data)
    media.exif = imaging.exif_summary(data)
    media.width, media.height = img.size
    media.quality = imaging.quality(img)
    media.phash = imaging.phash(img)
    media.embedding = imaging.lite_embedding(img)
    # Re-encode the private original: strips EXIF/GPS and any embedded payloads.
    big = img.copy()
    big.thumbnail((2400, 2400))
    return imaging.encode(big, "JPEG", 92), imaging.variants(img, sizes=(400, 800))


@handler("media.video_poster", queue="media", max_attempts=2, timeout_s=300)
async def make_video_poster(db: AsyncSession, job) -> dict:
    media = await db.get(Media, uuid.UUID(job.payload["id"]))
    if media is None:
        return {"skipped": True}
    data = await get_storage().get_private(media.storage_key)
    poster = await video.poster(data)
    if poster:
        key = f"public/{media.id}/poster.jpg"
        await get_storage().put_public(key, poster, "image/jpeg")
        media.variants = {**(media.variants or {}), "poster.jpg": key}
        await db.commit()
    return {"poster": bool(poster)}


async def publish_copy(db: AsyncSession, media: Media) -> str:
    """Make a public copy of a voice clip or video (only after consent)."""
    if media.public_key:
        return media.public_key
    ext = {"audio/webm": "webm", "video/webm": "webm", "audio/ogg": "ogg", "audio/mp4": "m4a", "video/mp4": "mp4",
           "audio/mpeg": "mp3", "audio/wav": "wav", "video/quicktime": "mov"}.get(media.mime, "bin")
    data = await get_storage().get_private(media.storage_key)
    key = f"public/{media.id}/media.{ext}"
    await get_storage().put_public(key, data, media.mime)
    media.public_key = key
    return key


async def owned_media(db: AsyncSession, media_id: uuid.UUID | str, user_id: uuid.UUID, kinds: set[str] | None = None) -> Media:
    m = await db.get(Media, uuid.UUID(str(media_id)))
    if m is None or m.owner_user_id != user_id:
        raise AppError(404, "media_not_found")
    if m.status != "ready":
        raise bad_request("media_not_ready")
    if kinds and m.kind not in kinds:
        raise bad_request("wrong_media_kind", expected=sorted(kinds))
    return m


def public_url(media: Media | None, variant: str | None = None) -> str | None:
    if media is None:
        return None
    key = (media.variants or {}).get(variant) if variant else None
    key = key or media.public_key
    return get_storage().public_url(key) if key else None
