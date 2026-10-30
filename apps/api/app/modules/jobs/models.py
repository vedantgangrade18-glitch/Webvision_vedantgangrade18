from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, JSONType, TimestampMixin


class Job(IdMixin, TimestampMixin, Base):
    """Mirrors background work for SSE progress (Part 2 §9.5)."""

    __tablename__ = "jobs"

    type: Mapped[str] = mapped_column(String(48), index=True)
    ref_type: Mapped[str | None] = mapped_column(String(32))
    ref_id: Mapped[str | None] = mapped_column(String(64), index=True)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)
    status: Mapped[str] = mapped_column(String(16), default="queued")  # queued|running|completed|failed
    progress: Mapped[int] = mapped_column(Integer, default=0)
    step: Mapped[str | None] = mapped_column(String(64))
    steps: Mapped[list] = mapped_column(JSONType, default=list)  # human-readable step log (agents)
    payload: Mapped[dict] = mapped_column(JSONType, default=dict)
    result: Mapped[dict | None] = mapped_column(JSONType)
    error: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    run_after: Mapped[datetime | None]
    started_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]
