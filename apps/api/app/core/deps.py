"""FastAPI dependencies: sessions, current user, roles, ownership, CSRF (Part 2 §11.1)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.errors import AppError
from app.core.i18n import normalise_locale
from app.core.security import decode_access_token, hmac_hash

ACCESS_COOKIE = "karu_at"
REFRESH_COOKIE = "karu_rt"
CSRF_COOKIE = "karu_csrf"
STAFF_ROLES = {"admin", "moderator", "ops"}
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


@dataclass
class Principal:
    user_id: uuid.UUID
    roles: list[str]
    amr: list[str]
    via_cookie: bool


def _extract(request: Request) -> tuple[str | None, bool]:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip(), False
    return request.cookies.get(ACCESS_COOKIE), True


def _check_csrf(request: Request, via_cookie: bool) -> None:
    if not via_cookie or request.method not in UNSAFE_METHODS:
        return
    cookie = request.cookies.get(CSRF_COOKIE)
    header = request.headers.get("x-csrf-token")
    if not cookie or not header or cookie != header:
        raise AppError(403, "csrf_failed")


async def optional_principal(request: Request) -> Principal | None:
    token, via_cookie = _extract(request)
    if not token:
        return None
    try:
        claims = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise AppError(401, "token_expired") from None
    except jwt.PyJWTError:
        return None
    _check_csrf(request, via_cookie)
    return Principal(uuid.UUID(claims["sub"]), claims.get("roles", []), claims.get("amr", []), via_cookie)


async def principal(p: Principal | None = Depends(optional_principal)) -> Principal:
    if p is None:
        raise AppError(401, "unauthorized")
    return p


async def current_user(p: Principal = Depends(principal), db: AsyncSession = Depends(get_db)):
    from app.modules.auth.models import User

    user = await db.get(User, p.user_id)
    if user is None or user.status == "deleted":
        raise AppError(401, "unauthorized")
    if user.status == "suspended" and not set(user.roles) & STAFF_ROLES:
        raise AppError(403, "account_suspended")
    return user


async def optional_user(p: Principal | None = Depends(optional_principal), db: AsyncSession = Depends(get_db)):
    if p is None:
        return None
    from app.modules.auth.models import User

    user = await db.get(User, p.user_id)
    if user is None or user.status != "active":
        return None
    return user


async def current_artisan(user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    from app.modules.artisans.models import ArtisanProfile

    if "artisan" not in user.roles:
        raise AppError(403, "not_an_artisan")
    profile = (await db.execute(select(ArtisanProfile).where(ArtisanProfile.user_id == user.id))).scalar_one_or_none()
    if profile is None:
        raise AppError(403, "not_an_artisan")
    return profile


def require_staff(*roles: str):
    allowed = set(roles) | {"admin"} if roles else STAFF_ROLES

    async def dep(p: Principal = Depends(principal), user=Depends(current_user)):
        from app.core.config import get_settings

        if not set(user.roles) & allowed:
            raise AppError(403, "staff_only")
        if get_settings().admin_totp_required and "totp" not in p.amr:
            raise AppError(403, "totp_required")
        return user

    return dep


def locale_dep(
    request: Request,
    accept_language: str | None = Header(default=None),
) -> str:
    cookie = request.cookies.get("NEXT_LOCALE") or request.query_params.get("locale")
    return normalise_locale(cookie or accept_language)


def ip_hash(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")
    return hmac_hash(ip, "ip")
