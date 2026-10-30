"""Tokens, hashing and application-level field encryption (Part 2 §11)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from datetime import timedelta

import jwt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import get_settings
from app.core.db import utcnow

ALGO = "HS256"


def _key(purpose: str) -> bytes:
    return hashlib.sha256(f"{purpose}:{get_settings().jwt_secret}".encode()).digest()


def hmac_hash(value: str, purpose: str = "lookup") -> str:
    """Deterministic keyed hash for lookups of encrypted values (phone, email)."""
    return hmac.new(_key(purpose), value.encode(), hashlib.sha256).hexdigest()


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def new_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def create_access_token(user_id: str, roles: list[str], *, amr: list[str] | None = None) -> str:
    s = get_settings()
    now = utcnow()
    payload = {
        "sub": user_id,
        "roles": roles,
        "amr": amr or ["otp"],
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=s.access_token_minutes)).timestamp()),
        "typ": "access",
    }
    return jwt.encode(payload, s.jwt_secret, algorithm=ALGO)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, get_settings().jwt_secret, algorithms=[ALGO], options={"require": ["exp", "sub"]})


def sign_payload(data: dict, minutes: int = 15) -> str:
    """Short-lived signed tokens (upload parts, signed media URLs, KYC state)."""
    payload = dict(data)
    payload["exp"] = int((utcnow() + timedelta(minutes=minutes)).timestamp())
    return jwt.encode(payload, _key("signed-url").hex(), algorithm=ALGO)


def verify_payload(token: str) -> dict:
    return jwt.decode(token, _key("signed-url").hex(), algorithms=[ALGO])


# ---- Field encryption (AES-GCM) for 🔒 columns -------------------------------------------


def _field_key() -> bytes:
    s = get_settings()
    if s.field_encryption_key:
        key = base64.b64decode(s.field_encryption_key)
        if len(key) != 32:
            raise ValueError("FIELD_ENCRYPTION_KEY must be 32 bytes, base64-encoded")
        return key
    if not s.is_dev:
        raise RuntimeError("FIELD_ENCRYPTION_KEY is required outside local/test")
    return _key("field-encryption")


def encrypt(value: str | None) -> str | None:
    if value is None or value == "":
        return value
    nonce = os.urandom(12)
    ct = AESGCM(_field_key()).encrypt(nonce, value.encode(), b"karu")
    return "v1:" + base64.urlsafe_b64encode(nonce + ct).decode()


def decrypt(value: str | None) -> str | None:
    if not value or not value.startswith("v1:"):
        return value
    raw = base64.urlsafe_b64decode(value[3:])
    return AESGCM(_field_key()).decrypt(raw[:12], raw[12:], b"karu").decode()


def mask_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    return phone[:3] + "•" * max(0, len(phone) - 7) + phone[-4:]
