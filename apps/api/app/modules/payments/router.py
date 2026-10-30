from __future__ import annotations

import json
import secrets
import uuid

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db, utcnow
from app.core.deps import current_user
from app.core.errors import AppError
from app.modules.orders.models import Order
from app.modules.orders.service import capture
from app.modules.payments.models import Refund, Transfer, WebhookEvent
from app.providers.payments import FakePayments, get_payments

router = APIRouter(tags=["payments"])


class VerifyIn(BaseModel):
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: str


async def _order_for_buyer(db: AsyncSession, order_id: str, user) -> Order:
    order = await db.get(Order, uuid.UUID(order_id))
    if order is None or order.buyer_user_id != user.id:
        raise AppError(404, "order_not_found")
    return order


@router.post("/orders/{order_id}/payment/verify")
async def verify_checkout(order_id: str, body: VerifyIn, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    """Checkout success handler. The webhook is the source of truth; this makes the UI instant."""
    order = await _order_for_buyer(db, order_id, user)
    provider = get_payments()
    if body.razorpay_order_id != order.rzp_order_id or not provider.verify_checkout_signature(
            body.razorpay_order_id, body.razorpay_payment_id, body.razorpay_signature):
        raise AppError(400, "payment_signature_invalid")
    payment = await provider.fetch_payment(body.razorpay_payment_id)
    if payment.get("status") == "authorized":
        # Auto-capture pending: the payment.captured webhook will complete the order.
        return {"ok": True, "status": "pending_capture"}
    if payment.get("status") != "captured":
        raise AppError(402, "payment_not_captured")
    await capture(db, order, payment_id=body.razorpay_payment_id, method=_method(payment),
                  amount_paise=int(payment.get("amount") or order.total * 100), raw=payment)
    await db.commit()
    return {"ok": True, "status": order.status}


def _method(p: dict) -> str | None:
    m = p.get("method")
    if m == "card" and (p.get("international") or (p.get("card") or {}).get("international")):
        return "intl_card"
    return m


class FakeCompleteIn(BaseModel):
    method: str = Field(default="upi", pattern="^(upi|card|netbanking|wallet|intl_card)$")
    outcome: str = Field(default="success", pattern="^(success|failure)$")


@router.post("/orders/{order_id}/payment/fake-complete")
async def fake_complete(order_id: str, body: FakeCompleteIn, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    """Test checkout used only when no Razorpay keys are configured (local demo, CI)."""
    provider = get_payments()
    if not isinstance(provider, FakePayments):
        raise AppError(404, "not_found")
    order = await _order_for_buyer(db, order_id, user)
    if body.outcome == "failure":
        return {"ok": False, "status": order.status, "error": "payment_failed"}
    payment_id = f"pay_fake{secrets.token_hex(6)}"
    signature = provider.sign(order.rzp_order_id, payment_id)
    if not provider.verify_checkout_signature(order.rzp_order_id, payment_id, signature):
        raise AppError(400, "payment_signature_invalid")
    await capture(db, order, payment_id=payment_id, method=body.method, amount_paise=int(order.total * 100),
                  raw={"fake": True, "method": body.method})
    await db.commit()
    return {"ok": True, "status": order.status}


@router.post("/webhooks/razorpay")
async def razorpay_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    raw = await request.body()
    provider = get_payments()
    if not provider.verify_webhook(raw, request.headers.get("x-razorpay-signature", "")):
        raise AppError(400, "webhook_signature_invalid")
    event = json.loads(raw)
    event_id = request.headers.get("x-razorpay-event-id") or event.get("id") or f"{event.get('event')}:{event.get('created_at')}"
    if (await db.execute(select(WebhookEvent.id).where(WebhookEvent.event_id == event_id))).first():
        return {"ok": True, "duplicate": True}
    etype = event.get("event", "")
    db.add(WebhookEvent(provider="razorpay", event_id=event_id, event_type=etype, payload=event))
    payload = event.get("payload") or {}
    if etype == "payment.captured":
        p = (payload.get("payment") or {}).get("entity") or {}
        order = (await db.execute(select(Order).where(Order.rzp_order_id == p.get("order_id")))).scalar_one_or_none()
        if order:
            await capture(db, order, payment_id=p["id"], method=_method(p), amount_paise=int(p.get("amount", 0)), raw=p)
    elif etype == "payment.failed":
        pass  # order stays pending; reservation expires on its own and the buyer can retry
    elif etype in ("refund.processed", "refund.failed"):
        r = (payload.get("refund") or {}).get("entity") or {}
        refund = (await db.execute(select(Refund).where(Refund.rzp_refund_id == r.get("id")))).scalar_one_or_none()
        if refund:
            refund.status = "processed" if etype == "refund.processed" else "failed"
    elif etype in ("transfer.processed", "transfer.failed", "transfer.settled"):
        tr_e = (payload.get("transfer") or {}).get("entity") or {}
        tr = (await db.execute(select(Transfer).where(Transfer.rzp_transfer_id == tr_e.get("id")))).scalar_one_or_none()
        if tr:
            if etype == "transfer.failed":
                tr.status, tr.failure_reason = "failed", str((tr_e.get("error") or {}).get("description") or "transfer_failed")[:255]
            elif etype == "transfer.settled" or tr_e.get("settlement_status") == "settled":
                tr.status = "settled"
    elif etype.startswith("account."):
        acc = (payload.get("account") or {}).get("entity") or {}
        from app.modules.artisans.models import ArtisanProfile
        from app.modules.payments.service import create_waiting_transfers

        prof = (await db.execute(select(ArtisanProfile).where(ArtisanProfile.razorpay_linked_account_id == acc.get("id")))).scalar_one_or_none()
        if prof:
            if etype in ("account.activated", "account.product.route.activated"):
                prof.payout_status = "active"
                await create_waiting_transfers(db, prof)
            elif etype in ("account.suspended", "account.rejected"):
                prof.payout_status, prof.payout_status_reason = "failed", etype
    ev = (await db.execute(select(WebhookEvent).where(WebhookEvent.event_id == event_id))).scalar_one()
    ev.processed_at = utcnow()
    await db.commit()
    return {"ok": True}
