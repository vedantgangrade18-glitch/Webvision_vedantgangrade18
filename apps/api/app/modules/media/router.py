from __future__ import annotations

import math
import uuid

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import ratelimit
from app.core.db import get_db, utcnow
from app.core.deps import STAFF_ROLES, current_user
from app.core.errors import AppError, bad_request
from app.core.i18n import normalise_locale
from app.core.security import sign_payload, verify_payload
from app.core.storage import PART_SIZE, get_storage
from app.modules.media.models import Media, Upload
from app.modules.media.service import MAX_BYTES, finalize, storage_key
from app.providers.stt import get_stt

router = APIRouter(tags=["media"])

EXT = {"photo": "jpg", "voice": "audio", "video": "video", "document": "doc"}


class UploadIn(BaseModel):
    kind: str = Field(pattern="^(photo|voice|video|document)$")
    mime: str
    bytes: int = Field(gt=0)
    duration_s: float | None = None


def _part_list(upload: Upload, media: Media, numbers: list[int]) -> list[dict]:
    st = get_storage()
    return [{"part_number": n, "url": st.part_url(str(media.id), media.storage_key, upload.s3_upload_id, n)} for n in numbers]


@router.post("/media/uploads")
async def start_upload(body: UploadIn, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    if body.bytes > MAX_BYTES[body.kind]:
        raise bad_request("file_too_large", max_bytes=MAX_BYTES[body.kind])
    await ratelimit.enforce(f"upload:{user.id}", 120, 3600)
    media = Media(owner_user_id=user.id, kind=body.kind, mime=body.mime[:64], bytes=body.bytes, storage_key="pending",
                  status="uploading", duration_s=body.duration_s, created_at=utcnow())
    db.add(media)
    await db.flush()
    media.storage_key = storage_key(media, EXT[body.kind])
    part_count = max(1, math.ceil(body.bytes / PART_SIZE))
    s3_id = await get_storage().start_multipart(media.storage_key, body.mime)
    upload = Upload(media_id=media.id, part_size=PART_SIZE, part_count=part_count, s3_upload_id=s3_id, received_parts=[])
    db.add(upload)
    await db.commit()
    return {"media_id": str(media.id), "part_size": PART_SIZE, "part_count": part_count,
            "parts": _part_list(upload, media, list(range(1, part_count + 1)))}


class PartsIn(BaseModel):
    part_numbers: list[int]


async def _upload_for(db: AsyncSession, media_id: str, user) -> tuple[Media, Upload]:
    from sqlalchemy import select

    media = await db.get(Media, uuid.UUID(media_id))
    if media is None or media.owner_user_id != user.id:
        raise AppError(404, "media_not_found")
    upload = (await db.execute(select(Upload).where(Upload.media_id == media.id))).scalar_one_or_none()
    if upload is None:
        raise AppError(404, "upload_not_found")
    return media, upload


@router.post("/media/uploads/{media_id}/parts")
async def more_parts(media_id: str, body: PartsIn, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    media, upload = await _upload_for(db, media_id, user)
    nums = [n for n in body.part_numbers if 1 <= n <= upload.part_count]
    return {"parts": _part_list(upload, media, nums), "received": upload.received_parts}


@router.put("/media/uploads/{media_id}/parts/{part_number}")
async def put_part(media_id: str, part_number: int, request: Request, token: str = Query(...),
                   db: AsyncSession = Depends(get_db)):
    """Local-storage stand-in for an S3 presigned part URL (token-authorised, no cookie)."""
    try:
        claims = verify_payload(token)
    except Exception:  # noqa: BLE001
        raise AppError(403, "invalid_upload_token") from None
    if claims.get("m") != media_id or claims.get("p") != part_number:
        raise AppError(403, "invalid_upload_token")
    from sqlalchemy import select

    media = await db.get(Media, uuid.UUID(media_id))
    upload = (await db.execute(select(Upload).where(Upload.media_id == uuid.UUID(media_id)))).scalar_one_or_none()
    if media is None or upload is None or media.status != "uploading":
        raise AppError(404, "upload_not_found")
    data = await request.body()
    if len(data) > upload.part_size or (part_number < upload.part_count and len(data) != upload.part_size):
        raise bad_request("bad_part_size")
    etag = await get_storage().write_part(media.storage_key, part_number, data)
    upload.received_parts = sorted(set(upload.received_parts or []) | {part_number})
    await db.commit()
    return Response(status_code=200, headers={"ETag": etag, "Access-Control-Expose-Headers": "ETag"})


class CompleteIn(BaseModel):
    parts: list[dict] = []  # [{part_number, etag}] (required for S3)
    duration_s: float | None = None


@router.post("/media/uploads/{media_id}/complete")
async def complete_upload(media_id: str, body: CompleteIn, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    media, upload = await _upload_for(db, media_id, user)
    if media.status == "ready":
        return _summary(media)
    await get_storage().complete_multipart(media.storage_key, upload.s3_upload_id, body.parts, upload.part_count)
    await finalize(db, media, body.duration_s or media.duration_s)
    await db.delete(upload)
    await db.commit()
    return _summary(media)


@router.post("/media/direct")
async def direct_upload(kind: str = Form(...), duration_s: float | None = Form(None), file: UploadFile = File(...),
                        user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    """Single-request upload for small files (≤ 15 MB), e.g. review photos, profile photo."""
    if kind not in MAX_BYTES:
        raise bad_request("invalid_kind")
    data = await file.read()
    if len(data) > min(MAX_BYTES[kind], 15 * 1024 * 1024):
        raise bad_request("file_too_large")
    await ratelimit.enforce(f"upload:{user.id}", 120, 3600)
    media = Media(owner_user_id=user.id, kind=kind, mime=(file.content_type or "application/octet-stream")[:64],
                  bytes=len(data), storage_key="pending", status="uploading", created_at=utcnow())
    db.add(media)
    await db.flush()
    media.storage_key = storage_key(media, EXT[kind])
    await get_storage().put_private(media.storage_key, data, media.mime)
    await finalize(db, media, duration_s)
    await db.commit()
    return _summary(media)


def _summary(m: Media) -> dict:
    st = get_storage()
    return {
        "id": str(m.id), "kind": m.kind, "status": m.status, "mime": m.mime, "bytes": m.bytes,
        "width": m.width, "height": m.height, "duration_s": m.duration_s, "quality": m.quality,
        "thumb_url": st.public_url(m.variants["400_4x5.jpg"]) if (m.variants or {}).get("400_4x5.jpg") else None,
        "url": st.public_url(m.public_key) if m.public_key else None,
        "poster_url": st.public_url(m.variants["poster.jpg"]) if (m.variants or {}).get("poster.jpg") else None,
    }


@router.get("/media/{media_id}")
async def get_media(media_id: str, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    m = await db.get(Media, uuid.UUID(media_id))
    is_staff = bool(set(user.roles) & STAFF_ROLES)
    if m is None or (m.owner_user_id != user.id and not is_staff):
        raise AppError(404, "media_not_found")
    out = _summary(m)
    out["private_url"] = f"/api/v1/media/private/{sign_payload({'k': m.storage_key, 'mime': m.mime}, minutes=10)}"
    return out


@router.get("/media/private/{token}")
async def private_media(token: str):
    """Short-lived signed URL for owners/staff (originals are never public)."""
    try:
        claims = verify_payload(token)
    except Exception:  # noqa: BLE001
        raise AppError(403, "link_expired") from None
    data = await get_storage().get_private(claims["k"])
    return Response(data, media_type=claims.get("mime") or "application/octet-stream",
                    headers={"Cache-Control": "private, max-age=300"})


@router.post("/stt")
async def stt(request: Request, file: UploadFile = File(...), locale: str | None = Form(None),
              client_transcript: str | None = Form(None), user=Depends(current_user)):
    """Short field dictation (≤ 15 s). p90 target < 3 s."""
    await ratelimit.enforce(f"stt:{user.id}", 60, 600)
    data = await file.read()
    if len(data) > 2 * 1024 * 1024:
        raise bad_request("audio_too_long", max_s=15)
    lang = normalise_locale(locale or user.locale)
    tr = await get_stt().transcribe(data, file.content_type or "audio/webm", lang, duration_s=15,
                                    client_transcript=client_transcript)
    return {"text": tr.text, "language": tr.language, "confidence": tr.confidence, "provider": tr.provider}
