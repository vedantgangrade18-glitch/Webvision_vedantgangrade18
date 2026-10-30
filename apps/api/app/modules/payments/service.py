"""Payments, Route transfers (payouts on hold) and refunds (Part 2 §10)."""

from __future__ import annotations

import logging
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.appconfig import get_config
from app.core.db import utcnow
from app.core.i18n import format_inr, pick_lang
from app.core.jobs import periodic
from app.modules.artisans.models import ArtisanProfile
from app.modules.catalog.models import Listing
from app.modules.orders.models import Order, OrderItem, Return
from app.modules.payments.models import Payment, Refund, Transfer
from app.providers.payments import get_payments

log = logging.getLogger("karu.payments")


def paise(amount: Decimal | float) -> int:
    return int((Decimal(str(amount)) * 100).quantize(Decimal("1")))


async def _payment_for(db: AsyncSession, order_id) -> Payment | None:
    return (await db.execute(select(Payment).where(Payment.order_id == order_id, Payment.status.in_(["captured", "refunded"]))
                             .order_by(Payment.created_at.desc()).limit(1))).scalar_one_or_none()


async def create_transfer_for_item(db: AsyncSession, item: OrderItem) -> Transfer:
    """0% commission: the artisan receives 100% of the item price, held until the return window closes."""
    existing = (await db.execute(select(Transfer).where(Transfer.order_item_id == item.id))).scalar_one_or_none()
    if existing:
        return existing
    tr = Transfer(order_item_id=item.id, artisan_id=item.artisan_id, amount=item.unit_price, on_hold=True,
                  status="awaiting_account")
    db.add(tr)
    await db.flush()
    profile = await db.get(ArtisanProfile, item.artisan_id)
    if profile.payout_status == "active" and profile.razorpay_linked_account_id:
        await _push_transfer(db, tr, item, profile)
    return tr


async def _push_transfer(db: AsyncSession, tr: Transfer, item: OrderItem, profile: ArtisanProfile) -> None:
    payment = await _payment_for(db, item.order_id)
    if payment is None:
        return
    try:
        res = await get_payments().create_transfer(payment.rzp_payment_id, profile.razorpay_linked_account_id,
                                                   paise(tr.amount), on_hold=True, notes={"order_item": str(item.id)})
        tr.rzp_transfer_id = res.get("id")
        tr.status = "on_hold"
    except Exception as exc:  # noqa: BLE001
        tr.status, tr.failure_reason = "failed", str(exc)[:255]


async def create_waiting_transfers(db: AsyncSession, profile: ArtisanProfile) -> int:
    rows = (await db.execute(select(Transfer, OrderItem).join(OrderItem, OrderItem.id == Transfer.order_item_id).where(
        Transfer.artisan_id == profile.id, Transfer.status.in_(["awaiting_account", "failed"])))).all()
    for tr, item in rows:
        if item.fulfilment_status in ("cancelled", "returned"):
            continue
        tr.failure_reason = None
        await _push_transfer(db, tr, item, profile)
    return len(rows)


async def refund_item(db: AsyncSession, item: OrderItem, reason: str) -> Refund:
    """Reverse the artisan transfer if already released, then refund the buyer."""
    from app.modules.notifications.service import notify

    existing = (await db.execute(select(Refund).where(Refund.order_item_id == item.id, Refund.status != "failed"))).scalar_one_or_none()
    if existing:
        return existing
    provider = get_payments()
    tr = (await db.execute(select(Transfer).where(Transfer.order_item_id == item.id))).scalar_one_or_none()
    if tr and tr.rzp_transfer_id and tr.status in ("released", "settled", "on_hold"):
        try:
            await provider.reverse_transfer(tr.rzp_transfer_id, paise(tr.amount))
            tr.status = "reversed"
        except Exception as exc:  # noqa: BLE001
            log.error("transfer reversal failed for %s: %s", item.id, exc)
            tr.failure_reason = f"reversal_failed: {exc}"[:255]
    elif tr:
        tr.status = "reversed"
    payment = await _payment_for(db, item.order_id)
    refund = Refund(order_item_id=item.id, amount=item.unit_price, reason=reason)
    db.add(refund)
    if payment is None:
        refund.status = "failed"
        return refund
    try:
        res = await provider.refund(payment.rzp_payment_id, paise(item.unit_price), {"order_item": str(item.id), "reason": reason})
        refund.rzp_refund_id = res.get("id")
        refund.status = "processed" if res.get("status") == "processed" else "pending"
    except Exception as exc:  # noqa: BLE001
        refund.status = "failed"
        log.error("refund failed for %s: %s", item.id, exc)
    order = await db.get(Order, item.order_id)
    if refund.status == "processed":
        await notify(db, order.buyer_user_id, "refund_processed",
                     {"amount": format_inr(item.unit_price), "order_number": order.order_number}, link=f"/account/orders/{order.id}")
    return refund


@periodic("payments.release_holds", every_s=3600)
async def release_holds(db: AsyncSession) -> None:
    """Release a transfer when delivered and (not returnable, or return window over) with no open return."""
    from app.modules.notifications.service import notify

    now = utcnow()
    rows = (await db.execute(select(Transfer, OrderItem).join(OrderItem, OrderItem.id == Transfer.order_item_id).where(
        Transfer.status == "on_hold", OrderItem.fulfilment_status == "delivered"))).all()
    for tr, item in rows:
        if item.returnable and (item.return_window_ends_at is None or item.return_window_ends_at > now):
            continue
        open_return = (await db.execute(select(Return.id).where(Return.order_item_id == item.id,
                                                                Return.status.in_(["requested", "received"])))).first()
        if open_return:
            continue
        listing = await db.get(Listing, item.listing_id)
        profile = await db.get(ArtisanProfile, item.artisan_id)
        title = pick_lang(listing.title, "en")[0] if listing else ""
        try:
            await get_payments().release_hold(tr.rzp_transfer_id)
            tr.status, tr.on_hold, tr.released_at = "released", False, now
            await notify(db, profile.user_id, "payout_sent", {"amount": format_inr(tr.amount), "title": title}, link="/sell/payouts")
        except Exception as exc:  # noqa: BLE001
            tr.status, tr.failure_reason = "failed", str(exc)[:255]
            await notify(db, profile.user_id, "payout_failed", {"amount": format_inr(tr.amount), "title": title}, link="/sell/payouts")


async def hold_until_for(db: AsyncSession, item: OrderItem):
    cfg = await get_config(db, "commerce.v1")
    if item.delivered_at is None:
        return None
    return item.delivered_at + timedelta(days=cfg["return_window_days"]) if item.returnable else item.delivered_at
