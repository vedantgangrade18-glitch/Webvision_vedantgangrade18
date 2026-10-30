from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, JSONType, TimestampMixin


class User(IdMixin, TimestampMixin, Base):
    __tablename__ = "users"

    phone_enc: Mapped[str | None] = mapped_column(String(255))  # 🔒 E.164
    phone_hash: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(320), unique=True, index=True)
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True)
    display_name: Mapped[str | None] = mapped_column(String(120))
    locale: Mapped[str] = mapped_column(String(5), default="en")
    roles: Mapped[list] = mapped_column(JSONType, default=lambda: ["buyer"])
    status: Mapped[str] = mapped_column(String(16), default="active")  # active|suspended|deleted
    last_login_at: Mapped[datetime | None]
    deleted_at: Mapped[datetime | None]
    # Preferences (A17 / B11)
    notification_prefs: Mapped[dict] = mapped_column(
        JSONType, default=lambda: {"whatsapp": True, "sms": True, "in_app": True, "email": True, "followed_makers": False}
    )
    voice_prompts: Mapped[bool] = mapped_column(Boolean, default=True)
    # Staff 2FA
    totp_secret_enc: Mapped[str | None] = mapped_column(String(255))
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)


class AuthOtp(IdMixin, TimestampMixin, Base):
    __tablename__ = "auth_otps"

    phone_or_email_hash: Mapped[str] = mapped_column(String(64), index=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime]
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    purpose: Mapped[str] = mapped_column(String(16), default="login")
    consumed_at: Mapped[datetime | None]


class RefreshToken(IdMixin, TimestampMixin, Base):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None]
    user_agent: Mapped[str | None] = mapped_column(String(255))
    ip_hash: Mapped[str | None] = mapped_column(String(64))
    amr: Mapped[list] = mapped_column(JSONType, default=lambda: ["otp"])


class Consent(IdMixin, TimestampMixin, Base):
    __tablename__ = "consents"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    consent_type: Mapped[str] = mapped_column(String(32))  # terms|privacy|public_voice|public_video|marketing
    version: Mapped[str] = mapped_column(String(16))
    granted_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None]
