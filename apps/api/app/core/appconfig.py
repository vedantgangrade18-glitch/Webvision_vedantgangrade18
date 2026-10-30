"""`app_config` defaults (Part 2 §17). Values live in the DB table so staff can edit them
in S06; this module provides defaults and a short in-process cache."""

from __future__ import annotations

import copy
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

DEFAULTS: dict[str, Any] = {
    "verification.v1": {
        "weights": {"L1": 0.35, "L2": 0.25, "L3": 0.40},
        "threshold": 70,
        "floors": {"L1": 40, "L3": 50},
        "new_artisan_l2_constant": 50,
        "l1": {"phash_match_hamming": 8, "max_originality_penalty": 40},
        "l3": {
            "weights": {"process": 0.40, "match": 0.35, "originality": 0.25},
            "min_duration_s": 20,
            "max_duration_s": 300,
            "max_keyframes": 120,
        },
        "periodic_rescan_days": 30,
    },
    "pricing.v1": {
        "cache_hours": 24,
        "min_samples_per_class": 4,
        "notify_change_pct": 15,
        "round_to_inr": 50,
        "stale_listing_refresh_days": 7,
    },
    "commerce.v1": {
        "reservation_minutes": 15,
        "return_window_days": 7,
        "auto_cancel_unshipped_days": 7,
        "auto_delivered_after_ship_days": 7,
        "low_stock_threshold": 3,
        "ship_reminder_days": [2, 4],
    },
    "limits.v1": {"regenerate_per_listing_per_day": 10, "voice_note_max_s": 120, "photos_max": 6},
    "budgets.v1": {"tinyfish_daily_inr": 2000, "gemini_daily_inr": 2000},
    # Estimated INR per call, used for the cost dashboard and budget breakers. Tune with real invoices.
    "costs.v1": {
        "tinyfish.search": 0.0,
        "tinyfish.fetch": 0.0,
        "tinyfish.agent": 8.0,
        "gemini.call": 0.25,
        "gemini.video": 1.5,
        "gemini.image": 11.5,
        "stt.minute": 0.5,
    },
    "passport.v1": {"min_reviews": 5, "min_avg_rating": 4.0},
    "flags": {"syndication.demo": False, "buyer.dark_mode": False, "demo_mode_recorded_providers": False},
    "categories.v1": [
        "sarees", "dupattas-stoles", "kurtas-fabric", "home-textiles", "pottery-terracotta", "woodcraft",
        "metal-brass", "jewellery", "bamboo-cane", "paintings", "leather", "toys", "other",
    ],
}

_CACHE: dict[str, tuple[float, Any]] = {}
_TTL = 30.0


def deep_merge(base: Any, override: Any) -> Any:
    if isinstance(base, dict) and isinstance(override, dict):
        out = copy.deepcopy(base)
        for k, v in override.items():
            out[k] = deep_merge(base.get(k), v) if k in base else copy.deepcopy(v)
        return out
    return copy.deepcopy(override)


async def get_config(db: AsyncSession, key: str) -> Any:
    now = time.monotonic()
    hit = _CACHE.get(key)
    if hit and now - hit[0] < _TTL:
        return copy.deepcopy(hit[1])
    from app.modules.admin.models import AppConfig

    row = (await db.execute(select(AppConfig).where(AppConfig.key == key))).scalar_one_or_none()
    default = DEFAULTS.get(key)
    value = deep_merge(default, row.value) if row and default is not None else (row.value if row else default)
    _CACHE[key] = (now, value)
    return copy.deepcopy(value)


def invalidate(key: str | None = None) -> None:
    if key is None:
        _CACHE.clear()
    else:
        _CACHE.pop(key, None)


async def flag(db: AsyncSession, name: str) -> bool:
    return bool((await get_config(db, "flags")).get(name, False))
