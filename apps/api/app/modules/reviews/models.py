from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, JSONType, TimestampMixin


class Review(IdMixin, TimestampMixin, Base):
    __tablename__ = "reviews"

    order_item_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("order_items.id", ondelete="CASCADE"), unique=True)
    buyer_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    listing_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("listings.id"), index=True)
    artisan_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("artisan_profiles.id"), index=True)
    rating: Mapped[int] = mapped_column(Integer)
    text: Mapped[str | None] = mapped_column(Text)
    photos: Mapped[list] = mapped_column(JSONType, default=list)
    status: Mapped[str] = mapped_column(String(16), default="published")  # published|hidden


class Wishlist(IdMixin, TimestampMixin, Base):
    __tablename__ = "wishlists"
    __table_args__ = (UniqueConstraint("user_id", "listing_id"),)

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    listing_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("listings.id", ondelete="CASCADE"))


class Follow(IdMixin, TimestampMixin, Base):
    __tablename__ = "follows"
    __table_args__ = (UniqueConstraint("user_id", "artisan_id"),)

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    artisan_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("artisan_profiles.id", ondelete="CASCADE"), index=True)
