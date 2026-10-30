from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, JSONType, TimestampMixin


class ArtisanProfile(IdMixin, TimestampMixin, Base):
    __tablename__ = "artisan_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    legal_name_enc: Mapped[str | None] = mapped_column(String(512))  # 🔒
    public_name: Mapped[str] = mapped_column(String(120))
    dob_enc: Mapped[str | None] = mapped_column(String(255))  # 🔒 ISO date
    gender: Mapped[str | None] = mapped_column(String(16))
    crafts: Mapped[list] = mapped_column(JSONType, default=list)  # craft slugs or free text
    years_of_practice: Mapped[int | None] = mapped_column(Integer)
    village_town: Mapped[str | None] = mapped_column(String(120))
    district: Mapped[str | None] = mapped_column(String(120))
    state: Mapped[str | None] = mapped_column(String(64))
    pin_code: Mapped[str | None] = mapped_column(String(6))
    lat: Mapped[float | None] = mapped_column(Float)  # rounded to ~1 km (2 decimals)
    lng: Mapped[float | None] = mapped_column(Float)
    story_text: Mapped[dict] = mapped_column(JSONType, default=dict)  # {lang: text}
    story_voice_media_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("media.id"))
    show_voice_publicly: Mapped[bool] = mapped_column(Boolean, default=True)
    profile_photo_media_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("media.id"))
    handle: Mapped[str] = mapped_column(String(48), unique=True, index=True)
    handle_edited: Mapped[bool] = mapped_column(Boolean, default=False)
    languages: Mapped[list] = mapped_column(JSONType, default=list)
    profile_completion: Mapped[int] = mapped_column(Integer, default=0)

    aadhaar_status: Mapped[str] = mapped_column(String(16), default="none")  # none|pending|verified|failed
    aadhaar_last4_enc: Mapped[str | None] = mapped_column(String(255))  # 🔒
    aadhaar_verified_at: Mapped[datetime | None]
    aadhaar_name_match: Mapped[bool | None] = mapped_column(Boolean)
    kyc_provider_ref: Mapped[str | None] = mapped_column(String(128))
    pehchan_card_no_enc: Mapped[str | None] = mapped_column(String(255))  # 🔒
    pehchan_status: Mapped[str] = mapped_column(String(16), default="none")
    pehchan_evidence_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    pehchan_checked_at: Mapped[datetime | None]
    gi_registration: Mapped[dict | None] = mapped_column(JSONType)
    linked_social_urls: Mapped[list] = mapped_column(JSONType, default=list)

    payout_status: Mapped[str] = mapped_column(String(16), default="none")  # none|pending_kyc|active|failed
    payout_method: Mapped[str | None] = mapped_column(String(8))  # upi|bank
    payout_details_enc: Mapped[str | None] = mapped_column(Text)  # 🔒 JSON {vpa} or {account_number, ifsc, name}
    payout_masked: Mapped[str | None] = mapped_column(String(64))
    razorpay_linked_account_id: Mapped[str | None] = mapped_column(String(64))
    razorpay_product_id: Mapped[str | None] = mapped_column(String(64))
    payout_status_reason: Mapped[str | None] = mapped_column(String(255))

    onboarding_completed_at: Mapped[datetime | None]
    dob_year: Mapped[int | None] = mapped_column(Integer)  # for age checks without decrypting


class Passport(IdMixin, TimestampMixin, Base):
    __tablename__ = "passports"

    artisan_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("artisan_profiles.id", ondelete="CASCADE"), unique=True)
    passport_code: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    state: Mapped[str] = mapped_column(String(16), default="unverified")  # unverified|verified|suspended
    state_reason: Mapped[str | None] = mapped_column(String(255))
    verified_at: Mapped[datetime | None]
    suspended_at: Mapped[datetime | None]
    last_evaluated_at: Mapped[datetime | None]
    staff_override: Mapped[bool] = mapped_column(Boolean, default=False)


def dob_from_iso(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None
