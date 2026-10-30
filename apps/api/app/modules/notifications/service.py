"""`notify(user, type, payload)` → one row per channel (Part 1 §4.6, Part 2 §9.7).

In-app rows are visible immediately; WhatsApp/SMS/email rows are sent by the `notify.send`
job. Non-urgent artisan messages respect quiet hours (21:00–08:00 IST).
"""

from __future__ import annotations

import uuid
from datetime import datetime, time, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import utcnow
from app.core.i18n import IST, t
from app.core.jobs import enqueue, handler
from app.modules.notifications.models import Notification

# type → (channels, urgent). "whatsapp|sms" means WhatsApp with SMS fallback.
EVENTS: dict[str, tuple[list[str], bool]] = {
    "listing_published": (["in_app", "whatsapp"], False),
    "verification_verified": (["in_app", "whatsapp"], False),
    "verification_not_verified": (["in_app", "whatsapp"], False),
    "new_order": (["in_app", "whatsapp|sms"], True),
    "ship_reminder": (["in_app", "whatsapp"], False),
    "order_confirmed": (["in_app", "email", "whatsapp|sms"], True),
    "order_shipped": (["in_app", "email", "whatsapp|sms"], True),
    "order_delivered": (["in_app", "email"], False),
    "order_cancelled": (["in_app", "email", "whatsapp|sms"], True),
    "refund_processed": (["in_app", "email"], True),
    "payout_sent": (["in_app", "whatsapp"], False),
    "payout_failed": (["in_app", "whatsapp"], False),
    "price_changed": (["in_app", "whatsapp"], False),
    "make_again_received": (["in_app", "whatsapp"], False),
    "make_again_answered": (["in_app", "email", "whatsapp"], False),
    "bulk_opportunity": (["in_app", "whatsapp"], False),
    "return_requested": (["in_app", "whatsapp", "email"], True),
    "maker_new_product": (["in_app", "email"], False),
    "passport_verified": (["in_app", "whatsapp"], False),
}

PREF_KEY = {"whatsapp": "whatsapp", "sms": "sms", "email": "email", "in_app": "in_app"}


def _next_morning_ist(now: datetime) -> datetime | None:
    local = now.astimezone(IST)
    if time(8, 0) <= local.time() < time(21, 0):
        return None
    day = local.date() if local.time() < time(8, 0) else local.date() + timedelta(days=1)
    return datetime.combine(day, time(8, 0), tzinfo=IST)


async def notify(db: AsyncSession, user_id: uuid.UUID, type_: str, payload: dict, *, link: str | None = None,
                 artisan_side: bool | None = None) -> list[Notification]:
    from app.modules.auth.models import User

    user = await db.get(User, user_id)
    if user is None or user.status != "active":
        return []
    channels, urgent = EVENTS.get(type_, (["in_app"], False))
    prefs = user.notification_prefs or {}
    if type_ == "maker_new_product" and not prefs.get("followed_makers"):
        return []
    body = t(f"notif.{type_}", user.locale, **{k: v for k, v in payload.items() if isinstance(v, (str, int, float))})
    is_artisan = "artisan" in user.roles if artisan_side is None else artisan_side
    delay_until = None if urgent or not is_artisan else _next_morning_ist(utcnow())
    rows = []
    for ch in channels:
        primary = ch.split("|")[0]
        if primary != "in_app" and not prefs.get(PREF_KEY[primary], True):
            if "|" in ch and prefs.get("sms", True):
                primary = "sms"
            else:
                continue
        if primary == "email" and not user.email:
            continue
        if primary in ("sms", "whatsapp") and not user.phone_enc:
            continue
        n = Notification(
            user_id=user.id, type=type_, channel=primary, template=f"karu_{type_}", locale=user.locale,
            payload={**payload, "_fallback_sms": "|" in ch}, body=body, link=link,
            status="sent" if primary == "in_app" else ("scheduled" if delay_until else "pending"),
            sent_at=utcnow() if primary == "in_app" else None, send_after=delay_until,
        )
        db.add(n)
        await db.flush()
        if primary != "in_app":
            delay = int((delay_until - utcnow()).total_seconds()) if delay_until else 0
            await enqueue(db, "notify.send", ref_type="notification", ref_id=str(n.id), payload={"id": str(n.id)},
                          delay_s=max(0, delay))
        rows.append(n)
    return rows


@handler("notify.send", queue="notify", max_attempts=3, timeout_s=60)
async def send_notification(db: AsyncSession, job) -> dict:
    from app.core.security import decrypt
    from app.modules.auth.models import User
    from app.providers.messaging import get_messaging

    n = await db.get(Notification, uuid.UUID(job.payload["id"]))
    if n is None or n.status in ("sent", "read"):
        return {"skipped": True}
    user = await db.get(User, n.user_id)
    if user is None or user.status != "active":
        n.status = "failed"
        n.error = "user_inactive"
        await db.commit()
        return {"skipped": True}
    m = get_messaging()
    params = [str(v) for k, v in n.payload.items() if not k.startswith("_")]
    try:
        if n.channel == "whatsapp":
            n.provider_ref = await m.send_whatsapp(decrypt(user.phone_enc), n.template, n.locale, params, n.body or "")
        elif n.channel == "sms":
            n.provider_ref = await m.send_sms(decrypt(user.phone_enc), n.body or "")
        elif n.channel == "email":
            subject = (n.body or "Karu")[:78]
            n.provider_ref = await m.send_email(user.email, subject, (n.body or "") + (f"\n\n{n.link}" if n.link else ""))
        n.status, n.sent_at = "sent", utcnow()
    except Exception as exc:  # noqa: BLE001
        n.error = str(exc)[:255]
        if n.channel == "whatsapp" and n.payload.get("_fallback_sms") and user.phone_enc:
            try:
                n.provider_ref = await m.send_sms(decrypt(user.phone_enc), n.body or "")
                n.status, n.sent_at, n.channel = "sent", utcnow(), "sms"
            except Exception as exc2:  # noqa: BLE001
                n.status, n.error = "failed", str(exc2)[:255]
        else:
            n.status = "failed"
    await db.commit()
    return {"status": n.status}
