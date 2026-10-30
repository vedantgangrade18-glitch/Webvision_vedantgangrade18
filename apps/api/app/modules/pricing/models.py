from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, Float, ForeignKey, Integer, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, JSONType, TimestampMixin


class PriceBenchmark(IdMixin, TimestampMixin, Base):
    __tablename__ = "price_benchmarks"

    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    descriptor: Mapped[dict] = mapped_column(JSONType, default=dict)  # category, craft, material, technique, size
    handmade_p25: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    handmade_median: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    handmade_p75: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    replica_p25: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    replica_median: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    replica_p75: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    sample_size_handmade: Mapped[int] = mapped_column(Integer, default=0)
    sample_size_replica: Mapped[int] = mapped_column(Integer, default=0)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    refreshed_at: Mapped[datetime | None]
    expires_at: Mapped[datetime | None]
    status: Mapped[str] = mapped_column(String(16), default="fresh")  # fresh|stale|failed|insufficient
    provider: Mapped[str] = mapped_column(String(16), default="tinyfish")
    queries: Mapped[list] = mapped_column(JSONType, default=list)


class PriceSource(IdMixin, TimestampMixin, Base):
    __tablename__ = "price_sources"

    benchmark_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("price_benchmarks.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(String(1024))
    domain: Mapped[str] = mapped_column(String(255))
    title: Mapped[str | None] = mapped_column(String(512))
    price_inr: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    klass: Mapped[str] = mapped_column("class", String(10))  # handmade|replica|unknown
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    fetched_at: Mapped[datetime | None]
    used: Mapped[bool] = mapped_column(Boolean, default=True)  # false when removed as an outlier


class ListingPriceAdvice(IdMixin, TimestampMixin, Base):
    __tablename__ = "listing_price_advice"

    listing_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("listings.id", ondelete="CASCADE"), index=True)
    benchmark_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("price_benchmarks.id", ondelete="SET NULL"))
    basis: Mapped[str] = mapped_column(String(10))  # handmade|replica
    position: Mapped[str] = mapped_column(String(10))  # below|in_range|above|unknown
    suggested_inr: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    message_key: Mapped[str] = mapped_column(String(48))
    price_at_advice: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    shown_at: Mapped[datetime | None]
    accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    notified_at: Mapped[datetime | None]
