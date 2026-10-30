"""Identifiers (Part 2 §4).

- Internal primary keys: UUIDv7 (time-sortable).
- Passport `KRP-` + 8 Crockford base32 chars, Karu ID `KRU-` + 8 chars (40 random bits).
- Product short code: 7 Crockford chars. Order number `KO-YYMMDD-XXXXX`.
Crockford base32 already excludes I, L, O and U.
"""

from __future__ import annotations

import os
import re
import secrets
import time
import unicodedata
import uuid
from datetime import datetime

CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_DECODE_MAP = {"O": "0", "I": "1", "L": "1"}


def uuid7() -> uuid.UUID:
    ts_ms = int(time.time() * 1000)
    rand = int.from_bytes(os.urandom(10), "big")
    value = (ts_ms & ((1 << 48) - 1)) << 80
    value |= 0x7 << 76  # version
    value |= ((rand >> 62) & 0xFFF) << 64  # rand_a (12 bits)
    value |= 0b10 << 62  # variant
    value |= rand & ((1 << 62) - 1)  # rand_b
    return uuid.UUID(int=value)


def random_code(length: int) -> str:
    return "".join(secrets.choice(CROCKFORD) for _ in range(length))


def new_passport_code() -> str:
    return f"KRP-{random_code(8)}"


def new_karu_id() -> str:
    return f"KRU-{random_code(8)}"


def new_short_code() -> str:
    return random_code(7)


def new_order_number(now: datetime) -> str:
    return f"KO-{now:%y%m%d}-{random_code(5)}"


def normalise_code(raw: str) -> str:
    """Case-insensitive input; tolerate the usual Crockford look-alikes."""
    raw = raw.strip().upper()
    prefix = ""
    m = re.match(r"^(KRU|KRP|KO)-(.*)$", raw)
    if m:
        prefix, raw = m.group(1) + "-", m.group(2)
    body = "".join(_DECODE_MAP.get(ch, ch) for ch in raw)
    return prefix + body


_KARU_ID_RE = re.compile(r"^KRU-[0-9A-HJKMNP-TV-Z]{8}$")
_SHORT_RE = re.compile(r"^[0-9A-HJKMNP-TV-Z]{7}$")


def is_karu_id(code: str) -> bool:
    return bool(_KARU_ID_RE.match(code))


def is_short_code(code: str) -> bool:
    return bool(_SHORT_RE.match(code))


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or "maker"


def new_handle(display_name: str) -> str:
    """Slug of the display name + 4 chars (lowercase for URLs)."""
    from app.core.translit import to_latin

    return f"{slugify(to_latin(display_name))[:24]}-{random_code(4).lower()}"
