from __future__ import annotations

import builtins
import uuid

from sqlalchemy import BigInteger, Float, ForeignKey, Integer, LargeBinary, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, JSONType, TimestampMixin


class Media(IdMixin, TimestampMixin, Base):
    __tablename__ = "media"

    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), index=True)
    # photo|voice|video|derived_image|share_image|document|evidence_screenshot
    kind: Mapped[str] = mapped_column(String(24))
    storage_key: Mapped[str] = mapped_column(String(512))  # private original
    public_key: Mapped[str | None] = mapped_column(String(512))  # public derivative (CDN)
    variants: Mapped[dict] = mapped_column(JSONType, default=dict)  # {"800_4x5_webp": key, ...}
    mime: Mapped[str] = mapped_column(String(64))
    bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    duration_s: Mapped[float | None] = mapped_column(Float)
    sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    phash: Mapped[str | None] = mapped_column(String(16), index=True)
    video_fingerprint: Mapped[builtins.bytes | None] = mapped_column(LargeBinary, nullable=True)  # noqa: UP007
    embedding: Mapped[list | None] = mapped_column(JSONType)  # image embedding (lite or SigLIP)
    exif: Mapped[dict | None] = mapped_column(JSONType)  # private; GPS never copied to derivatives
    quality: Mapped[dict | None] = mapped_column(JSONType)  # blur, brightness, min_side
    status: Mapped[str] = mapped_column(String(16), default="uploading")  # uploading|ready|failed|quarantined
    error: Mapped[str | None] = mapped_column(String(255))
    transcript: Mapped[dict | None] = mapped_column(JSONType)


class Upload(IdMixin, TimestampMixin, Base):
    """Multipart upload state (resumable across app restarts)."""

    __tablename__ = "uploads"

    media_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("media.id", ondelete="CASCADE"), unique=True)
    part_size: Mapped[int] = mapped_column(Integer)
    part_count: Mapped[int] = mapped_column(Integer)
    s3_upload_id: Mapped[str | None] = mapped_column(String(255))
    received_parts: Mapped[list] = mapped_column(JSONType, default=list)
