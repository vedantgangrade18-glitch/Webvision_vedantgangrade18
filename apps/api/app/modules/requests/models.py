from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, JSONType, TimestampMixin


class MakeAgainRequest(IdMixin, TimestampMixin, Base):
    __tablename__ = "make_again_requests"

    listing_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("listings.id", ondelete="CASCADE"), index=True)
    buyer_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    artisan_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("artisan_profiles.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    needed_by: Mapped[date | None] = mapped_column(Date)
    note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="open")  # open|replied|accepted|declined|expired
    artisan_reply: Mapped[dict | None] = mapped_column(JSONType)  # {price_inr, ready_in_days, message, declined}


class BulkRequest(IdMixin, TimestampMixin, Base):
    __tablename__ = "bulk_requests"

    org_name: Mapped[str] = mapped_column(String(160))
    contact_enc: Mapped[str] = mapped_column(Text)  # 🔒 JSON {name, phone, email}
    category_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("categories.id"))
    product_type: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)
    quantity: Mapped[int] = mapped_column(Integer)
    target_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    deadline: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(16), default="new")  # new|published|closed


class BulkOpportunity(IdMixin, TimestampMixin, Base):
    __tablename__ = "bulk_opportunities"

    bulk_request_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("bulk_requests.id", ondelete="CASCADE"), unique=True)
    published_at: Mapped[datetime]
    closes_at: Mapped[datetime | None]
    public_summary: Mapped[dict] = mapped_column(JSONType, default=dict)
    open: Mapped[bool] = mapped_column(Boolean, default=True)


class BulkResponse(IdMixin, TimestampMixin, Base):
    __tablename__ = "bulk_responses"
    __table_args__ = (UniqueConstraint("opportunity_id", "artisan_id"),)

    opportunity_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("bulk_opportunities.id", ondelete="CASCADE"), index=True)
    artisan_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("artisan_profiles.id"), index=True)
    quantity_offered: Mapped[int] = mapped_column(Integer)
    can_meet_deadline: Mapped[bool] = mapped_column(Boolean, default=True)
    note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="interested")  # interested|confirmed|declined
