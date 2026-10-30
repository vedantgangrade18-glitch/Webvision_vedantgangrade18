from __future__ import annotations

import json
from datetime import timedelta

import httpx
import pyotp
from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import ratelimit
from app.core.audit import audit
from app.core.config import get_settings
from app.core.db import get_db, utcnow
from app.core.deps import REFRESH_COOKIE, Principal, current_user, ip_hash, principal
from app.core.errors import AppError, bad_request
from app.core.i18n import LOCALES, normalise_locale, t
from app.core.security import decrypt, encrypt, hmac_hash, new_otp
from app.modules.auth.models import AuthOtp, Consent, User
from app.modules.auth.service import (
    CONSENT_VERSION,
    clear_session_cookies,
    issue_session,
    normalise_email,
    normalise_phone,
    revoke_all,
    rotate_refresh,
    serialize_user,
    user_by_email,
    user_by_phone,
)
from app.providers.messaging import get_messaging, messaging_is_fake

router = APIRouter(tags=["auth"])

OTP_TTL_MIN = 5
OTP_MAX_ATTEMPTS = 5


class OtpSendIn(BaseModel):
    phone: str | None = None
    email: str | None = None
    locale: str | None = None
    purpose: str = "login"


class OtpVerifyIn(BaseModel):
    phone: str | None = None
    email: str | None = None
    code: str = Field(min_length=6, max_length=6)
    locale: str | None = None


def _destination(body: OtpSendIn | OtpVerifyIn) -> tuple[str, str]:
    if body.phone:
        return "phone", normalise_phone(body.phone)
    if body.email:
        return "email", normalise_email(body.email)
    raise bad_request("phone_or_email_required")


async def _has_artisan(db: AsyncSession, user: User) -> bool:
    from app.modules.artisans.models import ArtisanProfile

    return (await db.execute(select(ArtisanProfile.id).where(ArtisanProfile.user_id == user.id))).first() is not None


@router.post("/auth/otp/send")
async def otp_send(body: OtpSendIn, request: Request, db: AsyncSession = Depends(get_db)):
    kind, dest = _destination(body)
    dest_hash = hmac_hash(dest, kind)
    await ratelimit.enforce(f"otp:dest:{dest_hash}", 3, 600, "otp_rate_limited")
    await ratelimit.enforce(f"otp:ip:{ip_hash(request)}", 20, 3600, "otp_rate_limited")
    last = (await db.execute(select(AuthOtp).where(AuthOtp.phone_or_email_hash == dest_hash)
                             .order_by(desc(AuthOtp.created_at)).limit(1))).scalar_one_or_none()
    if last and (utcnow() - last.created_at).total_seconds() < 30:
        raise AppError(429, "resend_too_soon", details={"retry_after_s": 30})
    code = new_otp()
    db.add(AuthOtp(phone_or_email_hash=dest_hash, code_hash=hmac_hash(code + dest_hash, "otp"),
                   expires_at=utcnow() + timedelta(minutes=OTP_TTL_MIN), purpose=body.purpose))
    await db.commit()
    locale = normalise_locale(body.locale)
    text = t("notif.otp", locale, code=code)
    # Web OTP API (Android autofill) needs the origin-bound last line.
    host = get_settings().public_base_url.split("://")[-1].split("/")[0]
    messaging = get_messaging()
    if kind == "phone":
        await messaging.send_sms(dest, f"{text}\n\n@{host} #{code}", template_vars={"otp": code})
    else:
        await messaging.send_email(dest, "Your Karu code", text)
    out = {"sent": True, "channel": "sms" if kind == "phone" else "email", "resend_after_s": 30, "expires_in_s": OTP_TTL_MIN * 60}
    if messaging_is_fake() and get_settings().is_dev:
        out["dev_code"] = code  # local/test only: no SMS provider configured
    return out


@router.post("/auth/otp/verify")
async def otp_verify(body: OtpVerifyIn, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    kind, dest = _destination(body)
    dest_hash = hmac_hash(dest, kind)
    otp = (await db.execute(select(AuthOtp).where(AuthOtp.phone_or_email_hash == dest_hash, AuthOtp.consumed_at.is_(None))
                            .order_by(desc(AuthOtp.created_at)).limit(1))).scalar_one_or_none()
    if otp is None:
        raise bad_request("otp_not_found")
    if otp.expires_at < utcnow():
        raise bad_request("otp_expired")
    if otp.attempts >= OTP_MAX_ATTEMPTS:
        raise AppError(429, "otp_too_many_attempts")
    if otp.code_hash != hmac_hash(body.code + dest_hash, "otp"):
        otp.attempts += 1
        await db.commit()
        raise bad_request("otp_wrong_code", attempts_left=OTP_MAX_ATTEMPTS - otp.attempts)
    otp.consumed_at = utcnow()

    user = await (user_by_phone(db, dest) if kind == "phone" else user_by_email(db, dest))
    is_new = user is None
    if user is None:
        user = User(locale=normalise_locale(body.locale), roles=["buyer"])
        if kind == "phone":
            user.phone_enc, user.phone_hash = encrypt(dest), hmac_hash(dest, "phone")
        else:
            user.email = dest
        db.add(user)
        await db.flush()
    if user.status == "deleted":
        raise AppError(403, "account_deleted")
    if user.status == "suspended":
        raise AppError(403, "account_suspended")
    session = await issue_session(db, request, response, user, ["otp"])
    await db.commit()
    return {"user": serialize_user(user, has_artisan=await _has_artisan(db, user)), "is_new": is_new,
            "csrf_token": session["csrf_token"]}


class GoogleIn(BaseModel):
    id_token: str
    locale: str | None = None


@router.post("/auth/google")
async def google_login(body: GoogleIn, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    s = get_settings()
    if not s.google_client_id:
        raise AppError(501, "google_not_configured")
    async with httpx.AsyncClient(timeout=10) as c:
        resp = await c.get("https://oauth2.googleapis.com/tokeninfo", params={"id_token": body.id_token})
    if resp.status_code != 200:
        raise AppError(401, "google_token_invalid")
    info = resp.json()
    if info.get("aud") != s.google_client_id or info.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        raise AppError(401, "google_token_invalid")
    if str(info.get("email_verified")).lower() != "true":
        raise AppError(401, "google_email_unverified")
    sub, email = info["sub"], normalise_email(info["email"])
    user = (await db.execute(select(User).where(User.google_sub == sub))).scalar_one_or_none() or await user_by_email(db, email)
    is_new = user is None
    if user is None:
        user = User(email=email, google_sub=sub, display_name=info.get("name"), locale=normalise_locale(body.locale), roles=["buyer"])
        db.add(user)
        await db.flush()
    else:
        user.google_sub = user.google_sub or sub
    if user.status != "active":
        raise AppError(403, f"account_{user.status}")
    session = await issue_session(db, request, response, user, ["google"])
    await db.commit()
    return {"user": serialize_user(user, has_artisan=await _has_artisan(db, user)), "is_new": is_new,
            "csrf_token": session["csrf_token"]}


@router.post("/auth/refresh")
async def refresh(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    user = await rotate_refresh(db, request, response, request.cookies.get(REFRESH_COOKIE))
    await db.commit()
    return {"ok": True, "user": serialize_user(user, has_artisan=await _has_artisan(db, user))}


@router.post("/auth/logout")
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    from app.core.security import token_hash
    from app.modules.auth.models import RefreshToken

    raw = request.cookies.get(REFRESH_COOKIE)
    if raw:
        row = (await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash(raw)))).scalar_one_or_none()
        if row and row.revoked_at is None:
            row.revoked_at = utcnow()
            await db.commit()
    clear_session_cookies(response)
    return {"ok": True}


# ---- Staff TOTP (mandatory 2FA, Part 2 §11.1) --------------------------------------------------


class TotpIn(BaseModel):
    code: str = Field(min_length=6, max_length=6)


def _require_staff_role(user: User) -> None:
    if not set(user.roles) & {"admin", "moderator", "ops"}:
        raise AppError(403, "staff_only")


@router.post("/auth/totp/setup")
async def totp_setup(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    _require_staff_role(user)
    if user.totp_enabled:
        raise AppError(409, "totp_already_enabled")
    secret = pyotp.random_base32()
    user.totp_secret_enc = encrypt(secret)
    await db.commit()
    label = user.email or user.display_name or str(user.id)[:8]
    return {"secret": secret, "otpauth_url": pyotp.TOTP(secret).provisioning_uri(name=label, issuer_name="Karu Admin")}


@router.post("/auth/totp/verify")
async def totp_verify(body: TotpIn, request: Request, response: Response, p: Principal = Depends(principal),
                      user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    _require_staff_role(user)
    await ratelimit.enforce(f"totp:{user.id}", 10, 600)
    secret = decrypt(user.totp_secret_enc)
    if not secret or not pyotp.TOTP(secret).verify(body.code, valid_window=1):
        raise bad_request("totp_wrong_code")
    first_time = not user.totp_enabled
    user.totp_enabled = True
    amr = sorted(set(p.amr) | {"totp"})
    session = await issue_session(db, request, response, user, amr)
    if first_time:
        await audit(db, user.id, "staff.totp_enabled", "user", str(user.id), ip_hash=ip_hash(request))
    await db.commit()
    return {"ok": True, "amr": amr, "csrf_token": session["csrf_token"]}


# ---- /me ------------------------------------------------------------------------------------


@router.get("/me")
async def me(p: Principal = Depends(principal), user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    out = serialize_user(user, has_artisan=await _has_artisan(db, user))
    out["amr"] = p.amr
    return out


class MePatch(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    locale: str | None = None
    voice_prompts: bool | None = None
    notification_prefs: dict | None = None


@router.patch("/me")
async def patch_me(body: MePatch, request: Request, response: Response, user: User = Depends(current_user),
                   db: AsyncSession = Depends(get_db)):
    if body.locale is not None:
        if body.locale not in LOCALES:
            raise bad_request("invalid_locale")
        user.locale = body.locale
        response.set_cookie("NEXT_LOCALE", body.locale, path="/", max_age=365 * 86400, samesite="lax")
    if body.display_name is not None:
        user.display_name = body.display_name.strip() or None
    if body.voice_prompts is not None:
        user.voice_prompts = body.voice_prompts
    if body.notification_prefs is not None:
        allowed = {"whatsapp", "sms", "in_app", "email", "followed_makers"}
        user.notification_prefs = {**user.notification_prefs,
                                   **{k: bool(v) for k, v in body.notification_prefs.items() if k in allowed}}
    await db.commit()
    return serialize_user(user, has_artisan=await _has_artisan(db, user))


class ConsentIn(BaseModel):
    consents: list[str]  # terms|privacy|public_voice|public_video|marketing
    revoke: list[str] = []


@router.post("/me/consents")
async def give_consents(body: ConsentIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    allowed = {"terms", "privacy", "public_voice", "public_video", "marketing"}
    now = utcnow()
    for c in body.consents:
        if c not in allowed:
            raise bad_request("invalid_consent", consent=c)
        db.add(Consent(user_id=user.id, consent_type=c, version=CONSENT_VERSION, granted_at=now))
    if body.revoke:
        rows = (await db.execute(select(Consent).where(Consent.user_id == user.id, Consent.consent_type.in_(body.revoke),
                                                       Consent.revoked_at.is_(None)))).scalars().all()
        for r in rows:
            r.revoked_at = now
    await db.commit()
    return {"ok": True, "version": CONSENT_VERSION}


@router.get("/me/consents")
async def list_consents(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Consent).where(Consent.user_id == user.id).order_by(Consent.granted_at))).scalars().all()
    active: dict[str, dict] = {}
    for r in rows:
        if r.revoked_at is None:
            active[r.consent_type] = {"version": r.version, "granted_at": r.granted_at.isoformat()}
        else:
            active.pop(r.consent_type, None)
    return {"active": active, "current_version": CONSENT_VERSION}


@router.delete("/me")
async def delete_me(request: Request, response: Response, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    """Soft delete now; PII hard-deleted by the purge job after 30 days (Part 2 §11.3)."""
    from app.modules.artisans.models import ArtisanProfile
    from app.modules.catalog.models import Listing

    user.status = "deleted"
    user.deleted_at = utcnow()
    profile = (await db.execute(select(ArtisanProfile).where(ArtisanProfile.user_id == user.id))).scalar_one_or_none()
    if profile:
        listings = (await db.execute(select(Listing).where(Listing.artisan_id == profile.id,
                                                           Listing.status.in_(["published", "paused", "draft"])))).scalars().all()
        for li in listings:
            li.status, li.deleted_at = "deleted", utcnow()
    await revoke_all(db, user.id)
    await audit(db, user.id, "user.self_delete", "user", str(user.id), ip_hash=ip_hash(request))
    await db.commit()
    clear_session_cookies(response)
    return {"ok": True, "hard_delete_after_days": 30}


@router.get("/me/export")
async def export_me(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    """DPDP right to access: everything Karu holds about the user, decrypted for them."""
    from app.modules.artisans.models import ArtisanProfile
    from app.modules.catalog.models import Listing
    from app.modules.orders.models import Address, Order
    from app.modules.reviews.models import Review

    profile = (await db.execute(select(ArtisanProfile).where(ArtisanProfile.user_id == user.id))).scalar_one_or_none()
    addresses = (await db.execute(select(Address).where(Address.user_id == user.id))).scalars().all()
    orders = (await db.execute(select(Order).where(Order.buyer_user_id == user.id))).scalars().all()
    reviews = (await db.execute(select(Review).where(Review.buyer_user_id == user.id))).scalars().all()
    consents = (await db.execute(select(Consent).where(Consent.user_id == user.id))).scalars().all()
    listings = []
    if profile:
        listings = (await db.execute(select(Listing).where(Listing.artisan_id == profile.id))).scalars().all()
    data = {
        "user": {**serialize_user(user), "phone": decrypt(user.phone_enc), "created_at": user.created_at.isoformat()},
        "artisan_profile": None if not profile else {
            "public_name": profile.public_name, "legal_name": decrypt(profile.legal_name_enc), "dob": decrypt(profile.dob_enc),
            "crafts": profile.crafts, "village_town": profile.village_town, "district": profile.district,
            "state": profile.state, "pin_code": profile.pin_code, "story": profile.story_text,
            "aadhaar_status": profile.aadhaar_status, "aadhaar_last4": decrypt(profile.aadhaar_last4_enc),
            "pehchan_status": profile.pehchan_status, "payout_status": profile.payout_status,
        },
        "addresses": [{"name": a.name, "phone": decrypt(a.phone_enc), "line1": a.line1, "line2": a.line2, "city": a.city,
                       "state": a.state, "pin": a.pin, "country": a.country} for a in addresses],
        "orders": [{"order_number": o.order_number, "status": o.status, "total": str(o.total), "created_at": o.created_at.isoformat()}
                   for o in orders],
        "reviews": [{"listing_id": str(r.listing_id), "rating": r.rating, "text": r.text} for r in reviews],
        "listings": [{"short_code": li.short_code, "title": li.title, "status": li.status} for li in listings],
        "consents": [{"type": c.consent_type, "version": c.version, "granted_at": c.granted_at.isoformat(),
                      "revoked_at": c.revoked_at.isoformat() if c.revoked_at else None} for c in consents],
        "exported_at": utcnow().isoformat(),
    }
    return Response(json.dumps(data, ensure_ascii=False, indent=2), media_type="application/json",
                    headers={"Content-Disposition": 'attachment; filename="karu-my-data.json"'})
