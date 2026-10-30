from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, Float, ForeignKey, Integer, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, JSONType, TimestampMixin


class VerificationRun(IdMixin, TimestampMixin, Base):
    __tablename__ = "verification_runs"

    listing_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("listings.id", ondelete="CASCADE"), index=True)
    listing_version: Mapped[int] = mapped_column(Integer)
    triggered_by: Mapped[str] = mapped_column(String(16))  # publish|edit|retry|periodic|admin|video
    status: Mapped[str] = mapped_column(String(16), default="queued")  # queued|running|completed|failed
    l1_score: Mapped[float | None] = mapped_column(Float)
    l2_score: Mapped[float | None] = mapped_column(Float)
    l3_score: Mapped[float | None] = mapped_column(Float)
    l2_mode: Mapped[str | None] = mapped_column(String(24))  # computed|new_artisan_constant
    karu_score: Mapped[float | None] = mapped_column(Float)
    verdict: Mapped[str | None] = mapped_column(String(16))  # verified|not_verified
    hard_fail: Mapped[bool] = mapped_column(Boolean, default=False)
    hard_fail_reason: Mapped[str | None] = mapped_column(String(255))
    config_snapshot: Mapped[dict] = mapped_column(JSONType, default=dict)
    artisan_tips: Mapped[list] = mapped_column(JSONType, default=list)  # message keys
    layer_status: Mapped[dict] = mapped_column(JSONType, default=dict)  # {L1: ok|needs_work, ...} for artisans
    deferred_checks: Mapped[list] = mapped_column(JSONType, default=list)  # web checks skipped by budget breaker
    started_at: Mapped[datetime | None]
    completed_at: Mapped[datetime | None]
    cost_inr: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    error: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0)


class VerificationLayerResult(IdMixin, TimestampMixin, Base):
    __tablename__ = "verification_layer_results"

    run_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("verification_runs.id", ondelete="CASCADE"), index=True)
    layer: Mapped[str] = mapped_column(String(2))  # L1|L2|L3
    score: Mapped[float | None] = mapped_column(Float)
    sub_scores: Mapped[dict] = mapped_column(JSONType, default=dict)
    evidence: Mapped[dict] = mapped_column(JSONType, default=dict)
    model_versions: Mapped[dict] = mapped_column(JSONType, default=dict)
    raw_response_ref: Mapped[dict | None] = mapped_column(JSONType)


class EvidenceItem(IdMixin, TimestampMixin, Base):
    __tablename__ = "evidence_items"

    run_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("verification_runs.id", ondelete="CASCADE"), index=True)
    artisan_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("artisan_profiles.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(24))  # registry_screenshot|web_match|price_source|video_analysis
    source_url: Mapped[str | None] = mapped_column(String(1024))
    captured_at: Mapped[datetime | None]
    media_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    summary: Mapped[dict] = mapped_column(JSONType, default=dict)


class ImageMatch(IdMixin, TimestampMixin, Base):
    __tablename__ = "image_matches"

    run_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)
    media_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("media.id", ondelete="CASCADE"), index=True)
    matched_url: Mapped[str] = mapped_column(String(1024))
    matched_domain: Mapped[str] = mapped_column(String(255))
    matched_media_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)  # internal match
    similarity: Mapped[float] = mapped_column(Float)
    first_seen_at: Mapped[datetime | None]
    is_own_channel: Mapped[bool] = mapped_column(Boolean, default=False)
