from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, JSONType, TimestampMixin, utcnow


class KaruId(IdMixin, TimestampMixin, Base):
    __tablename__ = "karu_ids"
    __table_args__ = (Index("ix_karu_ids_listing_status", "listing_id", "status"),)

    code: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    listing_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("listings.id", ondelete="CASCADE"))
    artisan_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("artisan_profiles.id", ondelete="CASCADE"), index=True)
    listing_version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(12), default="available")  # available|reserved|sold|returned|retired
    verification_run_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    reserved_until: Mapped[datetime | None]
    reserved_order_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    order_item_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    current_owner_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    owned_since: Mapped[datetime | None]
    sold_at: Mapped[datetime | None]
    sold_city: Mapped[str | None] = mapped_column(String(80))


class KaruIdEvent(IdMixin, Base):
    __tablename__ = "karu_id_events"

    karu_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("karu_ids.id", ondelete="CASCADE"), index=True)
    # created|reserved|released|sold|shipped|delivered|returned|retired|ownership_transferred|verified|revoked
    event: Mapped[str] = mapped_column(String(24))
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    data: Mapped[dict] = mapped_column(JSONType, default=dict)
    at: Mapped[datetime] = mapped_column(default=utcnow)


class ScanAggregate(IdMixin, Base):
    """Scans are aggregated hourly with no PII (Part 2 §9.4)."""

    __tablename__ = "scan_aggregates"
    __table_args__ = (Index("ix_scan_agg_target_hour", "target_type", "target_code", "hour", unique=True),)

    target_type: Mapped[str] = mapped_column(String(8))  # karu_id|listing
    target_code: Mapped[str] = mapped_column(String(12))
    hour: Mapped[datetime]
    count: Mapped[int] = mapped_column(Integer, default=0)
