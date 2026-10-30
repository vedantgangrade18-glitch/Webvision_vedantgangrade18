from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Index, Integer, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, JSONType, TimestampMixin


class Category(IdMixin, TimestampMixin, Base):
    __tablename__ = "categories"

    slug: Mapped[str] = mapped_column(String(64), unique=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("categories.id"))
    name: Mapped[dict] = mapped_column(JSONType, default=dict)  # {lang: name}
    attribute_schema: Mapped[dict] = mapped_column(JSONType, default=dict)
    icon: Mapped[str | None] = mapped_column(String(48))
    sort: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Craft(IdMixin, TimestampMixin, Base):
    __tablename__ = "crafts"

    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[dict] = mapped_column(JSONType, default=dict)
    description: Mapped[dict] = mapped_column(JSONType, default=dict)
    gi_tag: Mapped[bool] = mapped_column(Boolean, default=False)
    regions: Mapped[list] = mapped_column(JSONType, default=list)
    category_slug: Mapped[str | None] = mapped_column(String(64))
    technique_keywords: Mapped[list] = mapped_column(JSONType, default=list)
    hero_media_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("media.id"))


class Listing(IdMixin, TimestampMixin, Base):
    """One published product = one batch (Part 2 §5.2)."""

    __tablename__ = "listings"
    __table_args__ = (Index("ix_listings_status_cat_pub", "status", "category_id", "published_at"),)

    artisan_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("artisan_profiles.id", ondelete="CASCADE"), index=True)
    category_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("categories.id"))
    craft_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("crafts.id"))
    short_code: Mapped[str] = mapped_column(String(7), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(16), default="draft")  # draft|processing|published|paused|deleted
    hidden_by_staff: Mapped[bool] = mapped_column(Boolean, default=False)
    title: Mapped[dict] = mapped_column(JSONType, default=dict)
    description: Mapped[dict] = mapped_column(JSONType, default=dict)
    source_lang: Mapped[str] = mapped_column(String(5), default="hi")
    attributes: Mapped[dict] = mapped_column(JSONType, default=dict)
    tags: Mapped[list] = mapped_column(JSONType, default=list)
    price_inr: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    compare_at_inr: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    quantity_total: Mapped[int] = mapped_column(Integer, default=0)
    quantity_available: Mapped[int] = mapped_column(Integer, default=0)
    returnable: Mapped[bool] = mapped_column(Boolean, default=True)
    shipping: Mapped[dict] = mapped_column(JSONType, default=dict)
    verification_status: Mapped[str] = mapped_column(String(16), default="none")  # none|checking|verified|not_verified|revoked
    current_verification_run_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    verified_version: Mapped[int | None] = mapped_column(Integer)
    price_position: Mapped[str] = mapped_column(String(10), default="unknown")  # below|in_range|above|unknown
    current_benchmark_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    search_text: Mapped[str] = mapped_column(Text, default="")  # all languages, lowercased
    translit_text: Mapped[str] = mapped_column(Text, default="")  # phonetic Latin keys (§9.6)
    image_embedding: Mapped[list | None] = mapped_column(JSONType)
    version: Mapped[int] = mapped_column(Integer, default=1)
    field_confidence: Mapped[dict] = mapped_column(JSONType, default=dict)
    missing_fields: Mapped[list] = mapped_column(JSONType, default=list)
    notes_for_artisan: Mapped[list] = mapped_column(JSONType, default=list)
    published_at: Mapped[datetime | None]
    paused_at: Mapped[datetime | None]
    deleted_at: Mapped[datetime | None]
    views_count: Mapped[int] = mapped_column(Integer, default=0)
    share_count: Mapped[int] = mapped_column(Integer, default=0)
    rating_avg: Mapped[float | None]
    rating_count: Mapped[int] = mapped_column(Integer, default=0)
    regenerate_count: Mapped[int] = mapped_column(Integer, default=0)
    regenerate_day: Mapped[str | None] = mapped_column(String(10))
    last_viewed_at: Mapped[datetime | None]


class ListingVersion(IdMixin, TimestampMixin, Base):
    __tablename__ = "listing_versions"

    listing_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("listings.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict] = mapped_column(JSONType)
    changed_fields: Mapped[list] = mapped_column(JSONType, default=list)
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid)


class ListingMedia(IdMixin, TimestampMixin, Base):
    __tablename__ = "listing_media"

    listing_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("listings.id", ondelete="CASCADE"), index=True)
    media_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("media.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(16))  # photo|enhanced_photo|voice_note|making_video
    position: Mapped[int] = mapped_column(Integer, default=0)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    source_media_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)  # enhanced_photo → original
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class AiExtraction(IdMixin, TimestampMixin, Base):
    __tablename__ = "ai_extractions"

    listing_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("listings.id", ondelete="CASCADE"), index=True)
    input_media_ids: Mapped[list] = mapped_column(JSONType, default=list)
    transcript: Mapped[dict | None] = mapped_column(JSONType)
    extracted: Mapped[dict | None] = mapped_column(JSONType)
    field_confidence: Mapped[dict | None] = mapped_column(JSONType)
    model_versions: Mapped[dict] = mapped_column(JSONType, default=dict)
    cost_inr: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="completed")
    error: Mapped[str | None] = mapped_column(String(255))
