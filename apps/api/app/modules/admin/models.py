from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Integer, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, JSONType, TimestampMixin, utcnow


class Report(IdMixin, TimestampMixin, Base):
    __tablename__ = "reports"

    reporter_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    target_type: Mapped[str] = mapped_column(String(16))  # listing|karu_id|user|review
    target_id: Mapped[str] = mapped_column(String(64))
    reason: Mapped[str] = mapped_column(String(48))  # suspected_fake|copyright|prohibited|child_labour|other|hard_fail
    details: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="open")  # open|confirmed|dismissed|actioned
    source: Mapped[str] = mapped_column(String(16), default="user")  # user|system
    resolution_note: Mapped[str | None] = mapped_column(Text)


class AppConfig(Base):
    __tablename__ = "app_config"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict] = mapped_column(JSONType)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class AuditLog(IdMixin, Base):
    __tablename__ = "audit_log"

    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    action: Mapped[str] = mapped_column(String(64))
    target_type: Mapped[str | None] = mapped_column(String(32))
    target_id: Mapped[str | None] = mapped_column(String(64))
    before: Mapped[dict | None] = mapped_column(JSONType)
    after: Mapped[dict | None] = mapped_column(JSONType)
    reason: Mapped[str | None] = mapped_column(Text)
    ip_hash: Mapped[str | None] = mapped_column(String(64))
    at: Mapped[datetime] = mapped_column(default=utcnow, index=True)


class ExternalCall(IdMixin, Base):
    __tablename__ = "external_calls"
    __table_args__ = (Index("ix_external_calls_provider_at", "provider", "at"),)

    provider: Mapped[str] = mapped_column(String(16))  # tinyfish|gemini|stt|kyc|whatsapp|razorpay|sms|email
    operation: Mapped[str] = mapped_column(String(48))
    listing_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)
    run_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    cost_inr: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16))  # ok|error|skipped
    error: Mapped[str | None] = mapped_column(String(255))
    at: Mapped[datetime] = mapped_column(default=utcnow)
