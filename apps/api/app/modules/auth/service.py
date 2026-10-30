from __future__ import annotations

import re
import secrets
from datetime import timedelta

from fastapi import Request, Response
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import utcnow
from app.core.deps import ACCESS_COOKIE, CSRF_COOKIE, REFRESH_COOKIE, ip_hash
from app.core.errors import AppError, bad_request
from app.core.security import (
    create_access_token,
    decrypt,
    hmac_hash,
    mask_phone,
    new_refresh_token,
    token_hash,
)
from app.modules.auth.models import RefreshToken, User

CONSENT_VERSION = "2026-10"


def normalise_phone(raw: str, default_cc: str = "+91") -> str:
    digits = re.sub(r"[^\d+]", "", raw or "")
    if digits.startswith("00"):
        digits = "+" + digits[2:]
    if not digits.startswith("+"):
        digits = digits.lstrip("0")
        if len(digits) == 10:
            digits = default_cc + digits
        elif len(digits) == 12 and digits.startswith("91"):
            digits = "+" + digits
        else:
            digits = "+" + digits
    if not re.fullmatch(r"\+[1-9]\d{7,14}", digits):
        raise bad_request("invalid_phone")
    if digits.startswith("+91") and not re.fullmatch(r"\+91[6-9]\d{9}", digits):
        raise bad_request("invalid_phone")
    return digits


def normalise_email(raw: str) -> str:
    email = (raw or "").strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[a-z]{2,}", email):
        raise bad_request("invalid_email")
    return email


async def user_by_phone(db: AsyncSession, phone: str) -> User | None:
    return (await db.execute(select(User).where(User.phone_hash == hmac_hash(phone, "phone")))).scalar_one_or_none()


async def user_by_email(db: AsyncSession, email: str) -> User | None:
    return (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()


def serialize_user(user: User, *, has_artisan: bool = False) -> dict:
    return {
        "id": str(user.id),
        "display_name": user.display_name,
        "locale": user.locale,
        "roles": user.roles,
        "phone_masked": mask_phone(decrypt(user.phone_enc)) if user.phone_enc else None,
        "email": user.email,
        "is_artisan": "artisan" in user.roles,
        "has_artisan_profile": has_artisan,
        "is_staff": bool(set(user.roles) & {"admin", "moderator", "ops"}),
        "totp_enabled": user.totp_enabled,
        "voice_prompts": user.voice_prompts,
        "notification_prefs": user.notification_prefs,
        "status": user.status,
    }


def set_session_cookies(response: Response, access: str, refresh: str | None) -> str:
    s = get_settings()
    csrf = secrets.token_urlsafe(24)
    common = {"secure": s.cookie_secure, "samesite": "lax"}
    response.set_cookie(ACCESS_COOKIE, access, httponly=True, path="/", max_age=s.access_token_minutes * 60, **common)
    if refresh:
        response.set_cookie(REFRESH_COOKIE, refresh, httponly=True, path="/api/v1/auth",
                            max_age=s.refresh_token_days * 86400, **common)
    response.set_cookie(CSRF_COOKIE, csrf, httponly=False, path="/", max_age=s.refresh_token_days * 86400, **common)
    return csrf


def clear_session_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/api/v1/auth")
    response.delete_cookie(CSRF_COOKIE, path="/")


async def issue_session(db: AsyncSession, request: Request, response: Response, user: User, amr: list[str]) -> dict:
    s = get_settings()
    refresh = new_refresh_token()
    db.add(RefreshToken(
        user_id=user.id,
        token_hash=token_hash(refresh),
        expires_at=utcnow() + timedelta(days=s.refresh_token_days),
        user_agent=(request.headers.get("user-agent") or "")[:255],
        ip_hash=ip_hash(request),
        amr=amr,
    ))
    user.last_login_at = utcnow()
    access = create_access_token(str(user.id), user.roles, amr=amr)
    csrf = set_session_cookies(response, access, refresh)
    return {"access_token": access, "csrf_token": csrf, "expires_in": s.access_token_minutes * 60}


async def rotate_refresh(db: AsyncSession, request: Request, response: Response, raw: str | None) -> User:
    if not raw:
        raise AppError(401, "no_refresh_token")
    row = (await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash(raw)))).scalar_one_or_none()
    if row is None:
        raise AppError(401, "invalid_refresh_token")
    if row.revoked_at is not None:
        # Reuse of a rotated token → revoke the whole family (token theft signal).
        await db.execute(update(RefreshToken).where(RefreshToken.user_id == row.user_id, RefreshToken.revoked_at.is_(None))
                         .values(revoked_at=utcnow()))
        await db.commit()
        raise AppError(401, "refresh_token_reused")
    if row.expires_at < utcnow():
        raise AppError(401, "refresh_token_expired")
    user = await db.get(User, row.user_id)
    if user is None or user.status != "active":
        raise AppError(401, "unauthorized")
    row.revoked_at = utcnow()
    await issue_session(db, request, response, user, row.amr or ["otp"])
    return user


async def revoke_all(db: AsyncSession, user_id) -> None:
    await db.execute(update(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
                     .values(revoked_at=utcnow()))
