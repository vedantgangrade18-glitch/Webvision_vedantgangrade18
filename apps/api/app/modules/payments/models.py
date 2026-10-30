from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Index, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, JSONType, TimestampMixin


class Payment(IdMixin, TimestampMixin, Base):
    __tablename__ = "payments"

    order_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    rzp_payment_id: Mapped[str] = mapped_column(String(64), unique=True)
    method: Mapped[str | None] = mapped_column(String(16))  # upi|card|netbanking|wallet|intl_card
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(16))  # captured|failed|refunded
    raw: Mapped[dict] = mapped_column(JSONType, default=dict)


class Refund(IdMixin, TimestampMixin, Base):
    __tablename__ = "refunds"

    order_item_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("order_items.id", ondelete="CASCADE"), index=True)
    rzp_refund_id: Mapped[str | None] = mapped_column(String(64))
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending|processed|failed
    reason: Mapped[str] = mapped_column(String(32))


class Transfer(IdMixin, TimestampMixin, Base):
    """Payout of one order item to the artisan's Route linked account."""

    __tablename__ = "transfers"
    __table_args__ = (Index("ix_transfers_status_hold", "status", "hold_until"),)

    order_item_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("order_items.id", ondelete="CASCADE"), unique=True)
    artisan_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("artisan_profiles.id"), index=True)
    rzp_transfer_id: Mapped[str | None] = mapped_column(String(64))
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    on_hold: Mapped[bool] = mapped_column(Boolean, default=True)
    hold_until: Mapped[datetime | None]
    # awaiting_account|created|on_hold|released|settled|failed|reversed
    status: Mapped[str] = mapped_column(String(20), default="awaiting_account")
    failure_reason: Mapped[str | None] = mapped_column(String(255))
    released_at: Mapped[datetime | None]


class WebhookEvent(IdMixin, TimestampMixin, Base):
    """Idempotency for provider webhooks."""

    __tablename__ = "webhook_events"

    provider: Mapped[str] = mapped_column(String(16))
    event_id: Mapped[str] = mapped_column(String(128), unique=True)
    event_type: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSONType, default=dict)
    processed_at: Mapped[datetime | None]
