from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, JSONType, TimestampMixin


class Notification(IdMixin, TimestampMixin, Base):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(48))
    channel: Mapped[str] = mapped_column(String(12))  # in_app|whatsapp|sms|email
    template: Mapped[str] = mapped_column(String(64))
    locale: Mapped[str] = mapped_column(String(5))
    payload: Mapped[dict] = mapped_column(JSONType, default=dict)
    body: Mapped[str | None] = mapped_column(String(1024))
    link: Mapped[str | None] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(12), default="pending")  # pending|scheduled|sent|failed|read
    send_after: Mapped[datetime | None]
    sent_at: Mapped[datetime | None]
    read_at: Mapped[datetime | None]
    provider_ref: Mapped[str | None] = mapped_column(String(128))
    error: Mapped[str | None] = mapped_column(String(255))
