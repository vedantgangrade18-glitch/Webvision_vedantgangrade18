from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, JSONType, TimestampMixin


class BuyerProfile(IdMixin, TimestampMixin, Base):
    __tablename__ = "buyer_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    default_address_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    country: Mapped[str] = mapped_column(String(2), default="IN")
    currency_pref: Mapped[str] = mapped_column(String(3), default="INR")


class Address(IdMixin, TimestampMixin, Base):
    __tablename__ = "addresses"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    phone_enc: Mapped[str] = mapped_column(String(255))  # 🔒
    line1: Mapped[str] = mapped_column(String(255))
    line2: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str] = mapped_column(String(80))
    state: Mapped[str] = mapped_column(String(64))
    pin: Mapped[str] = mapped_column(String(10))
    country: Mapped[str] = mapped_column(String(2), default="IN")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)


class CartItem(IdMixin, TimestampMixin, Base):
    __tablename__ = "cart_items"
    __table_args__ = (UniqueConstraint("user_id", "listing_id"),)

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    listing_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("listings.id", ondelete="CASCADE"))
    qty: Mapped[int] = mapped_column(Integer, default=1)


class Order(IdMixin, TimestampMixin, Base):
    __tablename__ = "orders"

    order_number: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    buyer_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    # pending_payment|paid|cancelled|partially_shipped|completed|refunded
    status: Mapped[str] = mapped_column(String(20), default="pending_payment")
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    shipping_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    shipping_address: Mapped[dict] = mapped_column(JSONType)  # snapshot (phone encrypted inside)
    payment_provider: Mapped[str] = mapped_column(String(16), default="razorpay")
    rzp_order_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    reserved_until: Mapped[datetime | None]
    paid_at: Mapped[datetime | None]
    cancelled_at: Mapped[datetime | None]
    idempotency_key: Mapped[str | None] = mapped_column(String(80), unique=True)


class OrderItem(IdMixin, TimestampMixin, Base):
    __tablename__ = "order_items"
    __table_args__ = (Index("ix_order_items_artisan_fulfilment", "artisan_id", "fulfilment_status"),)

    order_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    listing_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("listings.id"))
    artisan_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("artisan_profiles.id"))
    karu_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("karu_ids.id"))
    title_snapshot: Mapped[str] = mapped_column(String(255))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    returnable: Mapped[bool] = mapped_column(Boolean, default=True)
    # pending|to_pack|shipped|delivered|return_requested|returned|cancelled
    fulfilment_status: Mapped[str] = mapped_column(String(20), default="pending")
    courier: Mapped[str | None] = mapped_column(String(64))
    tracking_no: Mapped[str | None] = mapped_column(String(64))
    shipped_at: Mapped[datetime | None]
    delivered_at: Mapped[datetime | None]
    return_window_ends_at: Mapped[datetime | None]
    reminders_sent: Mapped[list] = mapped_column(JSONType, default=list)
    delivery_disputed: Mapped[bool] = mapped_column(Boolean, default=False)


class Return(IdMixin, TimestampMixin, Base):
    __tablename__ = "returns"

    order_item_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("order_items.id", ondelete="CASCADE"), unique=True)
    reason: Mapped[str] = mapped_column(String(24))  # not_as_described|damaged|changed_mind|other
    details: Mapped[str | None] = mapped_column(Text)
    photos: Mapped[list] = mapped_column(JSONType, default=list)  # media ids
    status: Mapped[str] = mapped_column(String(16), default="requested")  # requested|received|refunded|rejected
    timeline: Mapped[list] = mapped_column(JSONType, default=list)
