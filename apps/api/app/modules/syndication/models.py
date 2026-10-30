from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, JSONType, TimestampMixin


class SyndicationJob(IdMixin, TimestampMixin, Base):
    """[DEMO] TinyFish Agent publishing a listing to a demo seller account."""

    __tablename__ = "syndication_jobs"

    listing_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("listings.id", ondelete="CASCADE"), index=True)
    portal: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default="queued")  # queued|running|completed|failed
    steps: Mapped[list] = mapped_column(JSONType, default=list)
    result_url: Mapped[str | None] = mapped_column(String(1024))
    job_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    streaming_url: Mapped[str | None] = mapped_column(String(1024))
