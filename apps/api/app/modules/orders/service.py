"""Orders: race-safe Karu ID reservation, payment capture, fulfilment timers (Part 2 §10)."""

from __future__ import annotations

import uuid
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.appconfig import get_config
from app.core.db import utcnow
from app.core.errors import AppError
from app.core.i18n import pick_lang
from app.core.ids import new_order_number
from app.core.jobs import periodic
from app.modules.artisans.models import ArtisanProfile
from app.modules.catalog.models import Listing
from app.modules.catalog.service import sync_quantity
from app.modules.karu_ids.models import KaruId, KaruIdEvent
from app.modules.orders.models import CartItem, Order, OrderItem
from app.modules.payments.models import Payment


async def reserve_units(db: AsyncSession, listing: Listing, qty: int, order_id: uuid.UUID, minutes: int) -> list[KaruId]:
    """Optimistic, portable reservation: conditional UPDATE … WHERE status='available' per unit.
    Two buyers racing for the last unit: exactly one UPDATE matches (Part 1 §11)."""
    until = utcnow() + timedelta(minutes=minutes)
    candidates = (await db.execute(select(KaruId.id).where(KaruId.listing_id == listing.id, KaruId.status == "available")
                                   .order_by(KaruId.created_at).limit(qty * 3 + 5))).scalars().all()
    got: list[uuid.UUID] = []
    for kid in candidates:
        res = await db.execute(update(KaruId).where(KaruId.id == kid, KaruId.status == "available")
                               .values(status="reserved", reserved_until=until, reserved_order_id=order_id)
                               .execution_options(synchronize_session=False))
        if res.rowcount == 1:
            got.append(kid)
            db.add(KaruIdEvent(karu_id=kid, event="reserved", data={"order_id": str(order_id)}))
            if len(got) == qty:
                break
    units = list((await db.execute(select(KaruId).where(KaruId.id.in_(got)))).scalars()) if got else []
    for u in units:
        await db.refresh(u)
    return units


async def release_units(db: AsyncSession, units: list[KaruId], reason: str) -> None:
    for u in units:
        if u.status == "reserved":
            u.status, u.reserved_until, u.reserved_order_id = "available", None, None
            db.add(KaruIdEvent(karu_id=u.id, event="released", data={"reason": reason}))


async def create_order(db: AsyncSession, user, address: dict, lines: list[tuple[Listing, int]], idem_key: str | None) -> Order:
    cfg = await get_config(db, "commerce.v1")
    if idem_key:
        existing = (await db.execute(select(Order).where(Order.idempotency_key == idem_key,
                                                         Order.buyer_user_id == user.id))).scalar_one_or_none()
        if existing:
            return existing
    order = Order(order_number=new_order_number(utcnow()), buyer_user_id=user.id, subtotal=Decimal(0), total=Decimal(0),
                  shipping_address=address, reserved_until=utcnow() + timedelta(minutes=cfg["reservation_minutes"]),
                  idempotency_key=idem_key)
    db.add(order)
    await db.flush()
    sold_out: list[str] = []
    all_units: list[KaruId] = []
    subtotal = Decimal(0)
    for listing, qty in lines:
        units = await reserve_units(db, listing, qty, order.id, cfg["reservation_minutes"])
        if len(units) < qty:
            sold_out.append(listing.short_code)
            all_units.extend(units)
            continue
        all_units.extend(units)
        title = pick_lang(listing.title, "en")[0]
        for u in units:
            db.add(OrderItem(order_id=order.id, listing_id=listing.id, artisan_id=listing.artisan_id, karu_id=u.id,
                             title_snapshot=title[:255], unit_price=listing.price_inr, returnable=listing.returnable,
                             fulfilment_status="pending"))
            subtotal += listing.price_inr
    if sold_out:
        await release_units(db, all_units, "sold_out_in_cart")
        await db.rollback()
        raise AppError(409, "just_sold_out", details={"codes": sold_out})
    order.subtotal = subtotal
    order.shipping_fee = Decimal(0)  # placeholder until shipping integration
    order.total = subtotal + order.shipping_fee
    for listing, _ in lines:
        await sync_quantity(db, listing)
    return order


async def capture(db: AsyncSession, order: Order, *, payment_id: str, method: str | None, amount_paise: int, raw: dict) -> bool:
    """Idempotent: webhook and checkout callback may both arrive, in any order."""
    from app.modules.notifications.service import notify
    from app.modules.payments.service import create_transfer_for_item, refund_item

    existing = (await db.execute(select(Payment).where(Payment.rzp_payment_id == payment_id))).scalar_one_or_none()
    if existing and order.status != "pending_payment":
        return False
    if amount_paise != int(order.total * 100):
        raise AppError(400, "amount_mismatch")
    if existing is None:
        db.add(Payment(order_id=order.id, rzp_payment_id=payment_id, method=method, amount=order.total, status="captured", raw=raw))
    if order.status != "pending_payment":
        return False
    now = utcnow()
    order.status, order.paid_at = "paid", now
    items = (await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))).scalars().all()
    await db.flush()
    city = (order.shipping_address or {}).get("city")
    touched: dict[uuid.UUID, Listing] = {}
    refunded: list[OrderItem] = []
    for item in items:
        unit = await db.get(KaruId, item.karu_id) if item.karu_id else None
        listing = touched.get(item.listing_id) or await db.get(Listing, item.listing_id)
        touched[listing.id] = listing
        if unit is None or unit.status != "reserved" or unit.reserved_order_id != order.id:
            # Reservation expired: allocate another unit if any, else refund this item (Part 1 §11).
            others = await reserve_units(db, listing, 1, order.id, 1)
            if not others:
                item.fulfilment_status = "cancelled"
                refunded.append(item)
                continue
            unit = others[0]
            item.karu_id = unit.id
        unit.status, unit.reserved_until = "sold", None
        unit.order_item_id = item.id
        unit.current_owner_user_id = order.buyer_user_id
        unit.owned_since = unit.sold_at = now
        unit.sold_city = city
        db.add(KaruIdEvent(karu_id=unit.id, event="sold", data={"order": order.order_number, "city": city}))
        item.fulfilment_status = "to_pack"
    await db.flush()
    for item in refunded:
        await refund_item(db, item, "sold_out_after_payment")
    if refunded and len(refunded) == len(items):
        order.status = "refunded"
    for listing in touched.values():
        await sync_quantity(db, listing)
    await db.execute(CartItem.__table__.delete().where(CartItem.user_id == order.buyer_user_id,
                                                       CartItem.listing_id.in_(list(touched.keys()))))
    buyer_first = ((order.shipping_address or {}).get("name") or "A buyer").split(" ")[0]
    for item in items:
        if item.fulfilment_status != "to_pack":
            continue
        await create_transfer_for_item(db, item)
        profile = await db.get(ArtisanProfile, item.artisan_id)
        unit = await db.get(KaruId, item.karu_id)
        await notify(db, profile.user_id, "new_order", {"buyer": buyer_first, "city": city or "", "title": item.title_snapshot,
                                                        "karu_id": unit.code}, link="/sell/orders")
    codes = [(await db.get(KaruId, i.karu_id)).code for i in items if i.fulfilment_status == "to_pack"]
    if codes:
        await notify(db, order.buyer_user_id, "order_confirmed", {"order_number": order.order_number, "karu_ids": ", ".join(codes)},
                     link=f"/account/orders/{order.id}", artisan_side=False)
    return True


@periodic("orders.release_reservations", every_s=60)
async def release_expired(db: AsyncSession) -> None:
    now = utcnow()
    units = (await db.execute(select(KaruId).where(KaruId.status == "reserved", KaruId.reserved_until < now))).scalars().all()
    listings: dict[uuid.UUID, Listing] = {}
    for u in units:
        u.status, u.reserved_until, u.reserved_order_id = "available", None, None
        db.add(KaruIdEvent(karu_id=u.id, event="released", data={"reason": "reservation_expired"}))
        listings[u.listing_id] = listings.get(u.listing_id) or await db.get(Listing, u.listing_id)
    for li in listings.values():
        await sync_quantity(db, li)
    stale = (await db.execute(select(Order).where(Order.status == "pending_payment",
                                                  Order.created_at < now - timedelta(hours=2)))).scalars().all()
    for o in stale:
        o.status, o.cancelled_at = "cancelled", now
        await db.execute(update(OrderItem).where(OrderItem.order_id == o.id).values(fulfilment_status="cancelled"))


@periodic("orders.fulfilment_timers", every_s=3600)
async def fulfilment_timers(db: AsyncSession) -> None:
    """Ship reminders (day 2, 4), auto-cancel unshipped (day 7) with refund, auto-deliver (ship + 7 days)."""
    from app.modules.notifications.service import notify
    from app.modules.payments.service import refund_item

    cfg = await get_config(db, "commerce.v1")
    now = utcnow()
    to_pack = (await db.execute(select(OrderItem, Order).join(Order, Order.id == OrderItem.order_id).where(
        OrderItem.fulfilment_status == "to_pack"))).all()
    for item, order in to_pack:
        age_days = (now - (order.paid_at or order.created_at)).total_seconds() / 86400
        if age_days >= cfg["auto_cancel_unshipped_days"]:
            item.fulfilment_status = "cancelled"
            unit = await db.get(KaruId, item.karu_id) if item.karu_id else None
            if unit:
                unit.status, unit.current_owner_user_id, unit.owned_since, unit.sold_at = "available", None, None, None
                db.add(KaruIdEvent(karu_id=unit.id, event="released", data={"reason": "auto_cancel_unshipped"}))
                await sync_quantity(db, await db.get(Listing, unit.listing_id))
            await refund_item(db, item, "auto_cancel_unshipped")
            await notify(db, order.buyer_user_id, "order_cancelled", {"order_number": order.order_number},
                         link=f"/account/orders/{order.id}", artisan_side=False)
            continue
        for day in cfg["ship_reminder_days"]:
            if age_days >= day and day not in (item.reminders_sent or []):
                profile = await db.get(ArtisanProfile, item.artisan_id)
                await notify(db, profile.user_id, "ship_reminder", {"order_number": order.order_number, "title": item.title_snapshot},
                             link="/sell/orders")
                item.reminders_sent = [*(item.reminders_sent or []), day]
    shipped = (await db.execute(select(OrderItem).where(OrderItem.fulfilment_status == "shipped",
                                                        OrderItem.delivery_disputed.is_(False)))).scalars().all()
    for item in shipped:
        if item.shipped_at and item.shipped_at + timedelta(days=cfg["auto_delivered_after_ship_days"]) <= now:
            await mark_delivered(db, item, auto=True)


async def mark_delivered(db: AsyncSession, item: OrderItem, *, auto: bool = False) -> None:
    from app.modules.notifications.service import notify
    from app.modules.payments.models import Transfer
    from app.modules.payments.service import hold_until_for

    cfg = await get_config(db, "commerce.v1")
    now = utcnow()
    item.fulfilment_status = "delivered"
    item.delivered_at = now
    item.return_window_ends_at = now + timedelta(days=cfg["return_window_days"]) if item.returnable else None
    unit = await db.get(KaruId, item.karu_id) if item.karu_id else None
    if unit:
        db.add(KaruIdEvent(karu_id=unit.id, event="delivered", data={"auto": auto}))
    tr = (await db.execute(select(Transfer).where(Transfer.order_item_id == item.id))).scalar_one_or_none()
    if tr:
        tr.hold_until = await hold_until_for(db, item)
    order = await db.get(Order, item.order_id)
    remaining = (await db.execute(select(OrderItem.id).where(OrderItem.order_id == order.id,
                                                             OrderItem.fulfilment_status.in_(["pending", "to_pack", "shipped"])))).first()
    if remaining is None:
        order.status = "completed"
    await notify(db, order.buyer_user_id, "order_delivered", {"order_number": order.order_number},
                 link=f"/account/orders/{order.id}", artisan_side=False)
