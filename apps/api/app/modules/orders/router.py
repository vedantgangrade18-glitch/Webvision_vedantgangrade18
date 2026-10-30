from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import ratelimit
from app.core.appconfig import get_config
from app.core.db import get_db, utcnow
from app.core.deps import current_artisan, current_user, locale_dep
from app.core.errors import AppError, bad_request
from app.core.i18n import format_inr, pick_lang, t
from app.core.security import decrypt, encrypt
from app.modules.artisans.models import ArtisanProfile
from app.modules.auth.service import normalise_phone
from app.modules.catalog.models import Listing
from app.modules.catalog.service import cards, primary_images
from app.modules.karu_ids.models import KaruId, KaruIdEvent
from app.modules.orders.models import Address, CartItem, Order, OrderItem, Return
from app.modules.orders.service import create_order, mark_delivered
from app.providers.payments import get_payments

router = APIRouter(tags=["orders"])


# ---- cart ---------------------------------------------------------------------------------------------


async def cart_view(db: AsyncSession, user, locale: str) -> dict:
    rows = (await db.execute(select(CartItem, Listing).join(Listing, Listing.id == CartItem.listing_id)
                             .where(CartItem.user_id == user.id).order_by(CartItem.created_at))).all()
    listing_cards = {c["id"]: c for c in await cards(db, [li for _, li in rows], locale, user.id)}
    groups: dict[str, dict] = {}
    total = 0.0
    for ci, li in rows:
        card = listing_cards[str(li.id)]
        available = li.status == "published" and not li.hidden_by_staff and li.quantity_available >= ci.qty
        key = str(li.artisan_id)
        g = groups.setdefault(key, {"maker": card["maker"], "items": []})
        g["items"].append({"listing_id": str(li.id), "qty": ci.qty, "card": card, "available": available,
                           "line_total": float(li.price_inr or 0) * ci.qty})
        if available:
            total += float(li.price_inr or 0) * ci.qty
    return {"groups": list(groups.values()), "subtotal_inr": total, "subtotal": format_inr(total),
            "count": sum(ci.qty for ci, _ in rows)}


@router.get("/cart/items")
async def get_cart(locale: str = Depends(locale_dep), user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    return await cart_view(db, user, locale)


class CartIn(BaseModel):
    listing_id: str
    qty: int = Field(default=1, ge=1, le=20)


@router.post("/cart/items")
async def add_cart(body: CartIn, locale: str = Depends(locale_dep), user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    li = await db.get(Listing, uuid.UUID(body.listing_id))
    if li is None or li.status != "published" or li.hidden_by_staff:
        raise AppError(404, "product_not_found")
    if li.quantity_available < 1:
        raise AppError(409, "out_of_stock")
    ci = (await db.execute(select(CartItem).where(CartItem.user_id == user.id, CartItem.listing_id == li.id))).scalar_one_or_none()
    if ci:
        ci.qty = min(body.qty + ci.qty, li.quantity_available, 20)
    else:
        db.add(CartItem(user_id=user.id, listing_id=li.id, qty=min(body.qty, li.quantity_available)))
    await db.commit()
    return await cart_view(db, user, locale)


@router.patch("/cart/items")
async def update_cart(body: CartIn, locale: str = Depends(locale_dep), user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    ci = (await db.execute(select(CartItem).where(CartItem.user_id == user.id,
                                                  CartItem.listing_id == uuid.UUID(body.listing_id)))).scalar_one_or_none()
    if ci is None:
        raise AppError(404, "cart_item_not_found")
    li = await db.get(Listing, ci.listing_id)
    ci.qty = max(1, min(body.qty, li.quantity_available or 1))
    await db.commit()
    return await cart_view(db, user, locale)


@router.delete("/cart/items/{listing_id}")
async def remove_cart(listing_id: str, locale: str = Depends(locale_dep), user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    ci = (await db.execute(select(CartItem).where(CartItem.user_id == user.id,
                                                  CartItem.listing_id == uuid.UUID(listing_id)))).scalar_one_or_none()
    if ci:
        await db.delete(ci)
        await db.commit()
    return await cart_view(db, user, locale)


# ---- addresses -----------------------------------------------------------------------------------------


class AddressIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str
    line1: str = Field(min_length=3, max_length=255)
    line2: str | None = Field(default=None, max_length=255)
    city: str = Field(min_length=2, max_length=80)
    state: str = Field(min_length=2, max_length=64)
    pin: str = Field(min_length=4, max_length=10)
    country: str = Field(default="IN", min_length=2, max_length=2)
    is_default: bool = False


def address_out(a: Address) -> dict:
    return {"id": str(a.id), "name": a.name, "phone": decrypt(a.phone_enc), "line1": a.line1, "line2": a.line2, "city": a.city,
            "state": a.state, "pin": a.pin, "country": a.country, "is_default": a.is_default}


@router.get("/addresses")
async def list_addresses(user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Address).where(Address.user_id == user.id).order_by(desc(Address.is_default),
                                                                                          Address.created_at))).scalars().all()
    return {"items": [address_out(a) for a in rows]}


@router.post("/addresses")
async def add_address(body: AddressIn, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    if body.country.upper() == "IN" and (not body.pin.isdigit() or len(body.pin) != 6):
        raise bad_request("invalid_pin")
    phone = normalise_phone(body.phone)
    count = len((await db.execute(select(Address.id).where(Address.user_id == user.id))).all())
    a = Address(user_id=user.id, name=body.name.strip(), phone_enc=encrypt(phone), line1=body.line1.strip(),
                line2=(body.line2 or "").strip() or None, city=body.city.strip(), state=body.state.strip(), pin=body.pin.strip(),
                country=body.country.upper(), is_default=body.is_default or count == 0)
    if a.is_default:
        for other in (await db.execute(select(Address).where(Address.user_id == user.id))).scalars():
            other.is_default = False
    db.add(a)
    await db.commit()
    return address_out(a)


@router.patch("/addresses/{address_id}")
async def edit_address(address_id: str, body: AddressIn, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    a = await db.get(Address, uuid.UUID(address_id))
    if a is None or a.user_id != user.id:
        raise AppError(404, "address_not_found")
    a.name, a.phone_enc, a.line1, a.line2 = body.name.strip(), encrypt(normalise_phone(body.phone)), body.line1.strip(), body.line2
    a.city, a.state, a.pin, a.country = body.city.strip(), body.state.strip(), body.pin.strip(), body.country.upper()
    if body.is_default:
        for other in (await db.execute(select(Address).where(Address.user_id == user.id))).scalars():
            other.is_default = other.id == a.id
    await db.commit()
    return address_out(a)


@router.delete("/addresses/{address_id}")
async def delete_address(address_id: str, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    a = await db.get(Address, uuid.UUID(address_id))
    if a is None or a.user_id != user.id:
        raise AppError(404, "address_not_found")
    await db.delete(a)
    await db.commit()
    return {"ok": True}


# ---- checkout --------------------------------------------------------------------------------------------


class OrderIn(BaseModel):
    address_id: str
    listing_ids: list[str] | None = None  # subset of cart ("Buy now" passes one)
    buy_now: dict | None = None  # {listing_id, qty} bypassing the cart


@router.post("/orders")
async def place_order(body: OrderIn, user=Depends(current_user), db: AsyncSession = Depends(get_db),
                      idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    await ratelimit.enforce(f"order:{user.id}", 20, 600)
    a = await db.get(Address, uuid.UUID(body.address_id))
    if a is None or a.user_id != user.id:
        raise AppError(404, "address_not_found")
    lines: list[tuple[Listing, int]] = []
    if body.buy_now:
        li = await db.get(Listing, uuid.UUID(body.buy_now["listing_id"]))
        if li is None or li.status != "published" or li.hidden_by_staff:
            raise AppError(404, "product_not_found")
        lines.append((li, max(1, min(int(body.buy_now.get("qty", 1)), 20))))
    else:
        q = select(CartItem, Listing).join(Listing, Listing.id == CartItem.listing_id).where(CartItem.user_id == user.id)
        if body.listing_ids:
            q = q.where(CartItem.listing_id.in_([uuid.UUID(x) for x in body.listing_ids]))
        for ci, li in (await db.execute(q)).all():
            if li.status == "published" and not li.hidden_by_staff:
                lines.append((li, ci.qty))
    if not lines:
        raise bad_request("cart_empty")
    snapshot = {"name": a.name, "phone_enc": a.phone_enc, "line1": a.line1, "line2": a.line2, "city": a.city, "state": a.state,
                "pin": a.pin, "country": a.country}
    order = await create_order(db, user, snapshot, lines, idempotency_key)
    provider = get_payments()
    if not order.rzp_order_id:
        rzp = await provider.create_order(int(order.total * 100), order.order_number, {"order_id": str(order.id)})
        order.rzp_order_id = rzp["id"]
    order.payment_provider = provider.name
    await db.commit()
    return {"order_id": str(order.id), "order_number": order.order_number, "amount_paise": int(order.total * 100),
            "currency": "INR", "provider": provider.name, "key_id": provider.key_id, "rzp_order_id": order.rzp_order_id,
            "reserved_until": order.reserved_until.isoformat() if order.reserved_until else None}


async def order_view(db: AsyncSession, order: Order, locale: str) -> dict:
    from app.modules.payments.models import Payment, Refund
    from app.modules.reviews.models import Review

    cfg = await get_config(db, "commerce.v1")
    items = (await db.execute(select(OrderItem).where(OrderItem.order_id == order.id).order_by(OrderItem.created_at))).scalars().all()
    images = await primary_images(db, list({i.listing_id for i in items}))
    out_items = []
    now = utcnow()
    for i in items:
        listing = await db.get(Listing, i.listing_id)
        profile = await db.get(ArtisanProfile, i.artisan_id)
        unit = await db.get(KaruId, i.karu_id) if i.karu_id else None
        ret = (await db.execute(select(Return).where(Return.order_item_id == i.id))).scalar_one_or_none()
        reviewed = (await db.execute(select(Review.id).where(Review.order_item_id == i.id))).first() is not None
        refund = (await db.execute(select(Refund).where(Refund.order_item_id == i.id))).scalar_one_or_none()
        can_return = (i.returnable and i.fulfilment_status == "delivered" and ret is None and i.return_window_ends_at
                      and i.return_window_ends_at > now)
        out_items.append({
            "id": str(i.id), "title": pick_lang(listing.title, locale)[0] if listing else i.title_snapshot,
            "code": listing.short_code if listing else None, "image": images.get(i.listing_id),
            "price_inr": float(i.unit_price), "maker": {"name": profile.public_name, "handle": profile.handle},
            "karu_id": unit.code if unit and i.fulfilment_status not in ("pending", "cancelled") else None,
            "status": i.fulfilment_status, "courier": i.courier, "tracking_no": i.tracking_no,
            "shipped_at": i.shipped_at.isoformat() if i.shipped_at else None,
            "delivered_at": i.delivered_at.isoformat() if i.delivered_at else None,
            "returnable": i.returnable, "return_window_ends_at": i.return_window_ends_at.isoformat() if i.return_window_ends_at else None,
            "can_return": bool(can_return), "can_confirm_received": i.fulfilment_status == "shipped",
            "can_review": i.fulfilment_status in ("delivered",) and not reviewed, "reviewed": reviewed,
            "return": {"status": ret.status, "reason": ret.reason} if ret else None,
            "refund": {"status": refund.status, "amount_inr": float(refund.amount)} if refund else None,
        })
    payment = (await db.execute(select(Payment).where(Payment.order_id == order.id))).scalars().first()
    addr = dict(order.shipping_address or {})
    addr["phone"] = decrypt(addr.pop("phone_enc", None))
    return {"id": str(order.id), "order_number": order.order_number, "status": order.status, "total_inr": float(order.total),
            "total": format_inr(order.total), "subtotal_inr": float(order.subtotal), "shipping_fee_inr": float(order.shipping_fee),
            "created_at": order.created_at.isoformat(), "paid_at": order.paid_at.isoformat() if order.paid_at else None,
            "payment": {"method": payment.method, "status": payment.status} if payment else None,
            "address": addr, "items": out_items, "return_window_days": cfg["return_window_days"]}


@router.get("/orders")
async def my_orders(locale: str = Depends(locale_dep), user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Order).where(Order.buyer_user_id == user.id, Order.status != "pending_payment")
                             .order_by(desc(Order.created_at)).limit(100))).scalars().all()
    return {"items": [await order_view(db, o, locale) for o in rows]}


async def _my_order(db: AsyncSession, order_id: str, user) -> Order:
    try:
        o = await db.get(Order, uuid.UUID(order_id))
    except ValueError:
        o = None
    if o is None or o.buyer_user_id != user.id:
        raise AppError(404, "order_not_found")
    return o


@router.get("/orders/{order_id}")
async def get_order(order_id: str, locale: str = Depends(locale_dep), user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    return await order_view(db, await _my_order(db, order_id, user), locale)


async def _my_item(db: AsyncSession, order: Order, item_id: str) -> OrderItem:
    item = await db.get(OrderItem, uuid.UUID(item_id))
    if item is None or item.order_id != order.id:
        raise AppError(404, "order_item_not_found")
    return item


@router.post("/orders/{order_id}/items/{item_id}/received")
async def confirm_received(order_id: str, item_id: str, locale: str = Depends(locale_dep), user=Depends(current_user),
                           db: AsyncSession = Depends(get_db)):
    order = await _my_order(db, order_id, user)
    item = await _my_item(db, order, item_id)
    if item.fulfilment_status != "shipped":
        raise AppError(409, "not_shipped")
    await mark_delivered(db, item)
    await db.commit()
    return await order_view(db, order, locale)


class DisputeIn(BaseModel):
    note: str | None = Field(default=None, max_length=500)


@router.post("/orders/{order_id}/items/{item_id}/not-received")
async def dispute_delivery(order_id: str, item_id: str, body: DisputeIn, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    """Stops the automatic 'delivered' timer; ops follow up (Part 2 §10 delivery confirmation)."""
    from app.modules.admin.models import Report

    order = await _my_order(db, order_id, user)
    item = await _my_item(db, order, item_id)
    item.delivery_disputed = True
    db.add(Report(reporter_user_id=user.id, target_type="listing", target_id=str(item.listing_id), reason="not_received",
                  details=f"{order.order_number}: {body.note or ''}"))
    await db.commit()
    return {"ok": True}


class ReturnIn(BaseModel):
    reason: str = Field(pattern="^(not_as_described|damaged|changed_mind|other)$")
    details: str | None = Field(default=None, max_length=1000)
    photo_media_ids: list[str] = Field(default_factory=list, max_length=4)


@router.post("/orders/{order_id}/items/{item_id}/return")
async def request_return(order_id: str, item_id: str, body: ReturnIn, locale: str = Depends(locale_dep), user=Depends(current_user),
                         db: AsyncSession = Depends(get_db)):
    from app.modules.media.service import owned_media
    from app.modules.notifications.service import notify

    order = await _my_order(db, order_id, user)
    item = await _my_item(db, order, item_id)
    if not item.returnable:
        raise AppError(409, "not_returnable")
    if item.fulfilment_status != "delivered" or not item.return_window_ends_at or item.return_window_ends_at < utcnow():
        raise AppError(409, "return_window_closed")
    if (await db.execute(select(Return.id).where(Return.order_item_id == item.id))).first():
        raise AppError(409, "return_exists")
    photos = [str((await owned_media(db, m, user.id, {"photo"})).id) for m in body.photo_media_ids]
    db.add(Return(order_item_id=item.id, reason=body.reason, details=body.details, photos=photos,
                  timeline=[{"at": utcnow().isoformat(), "status": "requested"}]))
    item.fulfilment_status = "return_requested"
    from app.modules.auth.models import User

    profile = await db.get(ArtisanProfile, item.artisan_id)
    maker_user = await db.get(User, profile.user_id)
    await notify(db, profile.user_id, "return_requested", {"order_number": order.order_number, "title": item.title_snapshot,
                                                           "reason": t(f"return_reason.{body.reason}", maker_user.locale)},
                 link="/sell/orders?tab=returns")
    await db.commit()
    return await order_view(db, order, locale)


# ---- artisan side (A13) ---------------------------------------------------------------------------------------


@router.get("/artisan/orders")
async def artisan_orders(status: str | None = None, locale: str = Depends(locale_dep), p: ArtisanProfile = Depends(current_artisan),
                         db: AsyncSession = Depends(get_db)):
    groups = {"to_pack": ["to_pack"], "shipped": ["shipped"], "delivered": ["delivered"],
              "returns": ["return_requested", "returned"]}
    q = (select(OrderItem, Order, Listing).join(Order, Order.id == OrderItem.order_id).join(Listing, Listing.id == OrderItem.listing_id)
         .where(OrderItem.artisan_id == p.id, OrderItem.fulfilment_status.not_in(["pending", "cancelled"])))
    if status in groups:
        q = q.where(OrderItem.fulfilment_status.in_(groups[status]))
    rows = (await db.execute(q.order_by(desc(Order.paid_at)))).all()
    images = await primary_images(db, list({li.id for _, _, li in rows}))
    items = []
    for item, order, li in rows:
        addr = dict(order.shipping_address or {})
        unit = await db.get(KaruId, item.karu_id) if item.karu_id else None
        ret = (await db.execute(select(Return).where(Return.order_item_id == item.id))).scalar_one_or_none()
        items.append({
            "id": str(item.id), "order_number": order.order_number, "status": item.fulfilment_status,
            "title": pick_lang(li.title, locale)[0], "image": images.get(li.id), "price_inr": float(item.unit_price),
            "karu_id": unit.code if unit else None, "paid_at": order.paid_at.isoformat() if order.paid_at else None,
            "buyer": {"first_name": (addr.get("name") or "").split(" ")[0], "city": addr.get("city")},
            # Full address and phone are shown to the maker only for packing; never public.
            "ship_to": {"name": addr.get("name"), "line1": addr.get("line1"), "line2": addr.get("line2"), "city": addr.get("city"),
                        "state": addr.get("state"), "pin": addr.get("pin"), "phone": decrypt(addr.get("phone_enc"))},
            "courier": item.courier, "tracking_no": item.tracking_no,
            "shipped_at": item.shipped_at.isoformat() if item.shipped_at else None,
            "return": {"id": str(ret.id), "status": ret.status, "reason": ret.reason, "details": ret.details} if ret else None,
        })
    counts = {}
    for key, sts in groups.items():
        counts[key] = len((await db.execute(select(OrderItem.id).where(OrderItem.artisan_id == p.id,
                                                                       OrderItem.fulfilment_status.in_(sts)))).all())
    return {"items": items, "counts": counts}


class ShipIn(BaseModel):
    courier: str | None = Field(default=None, max_length=64)
    tracking_no: str | None = Field(default=None, max_length=64)


@router.post("/artisan/orders/items/{item_id}/ship")
async def ship(item_id: str, body: ShipIn, p: ArtisanProfile = Depends(current_artisan), db: AsyncSession = Depends(get_db)):
    from app.modules.notifications.service import notify

    item = await db.get(OrderItem, uuid.UUID(item_id))
    if item is None or item.artisan_id != p.id:
        raise AppError(404, "order_item_not_found")
    if item.fulfilment_status != "to_pack":
        raise AppError(409, "not_to_pack")
    item.fulfilment_status, item.shipped_at = "shipped", utcnow()
    item.courier, item.tracking_no = body.courier, body.tracking_no
    order = await db.get(Order, item.order_id)
    if order.status == "paid":
        order.status = "partially_shipped"
    if item.karu_id:
        db.add(KaruIdEvent(karu_id=item.karu_id, event="shipped", data={"courier": body.courier}))
    tracking = f"{body.courier or ''} {body.tracking_no or ''}".strip()
    await notify(db, order.buyer_user_id, "order_shipped", {"order_number": order.order_number, "title": item.title_snapshot,
                                                            "tracking": tracking}, link=f"/account/orders/{order.id}", artisan_side=False)
    await db.commit()
    return {"status": item.fulfilment_status}


@router.post("/artisan/returns/{return_id}/receive")
async def receive_return(return_id: str, p: ArtisanProfile = Depends(current_artisan), db: AsyncSession = Depends(get_db)):
    """Artisan confirms the piece came back → refund via provider → unit `returned` (F8)."""
    from app.modules.catalog.service import sync_quantity
    from app.modules.payments.service import refund_item

    ret = await db.get(Return, uuid.UUID(return_id))
    item = await db.get(OrderItem, ret.order_item_id) if ret else None
    if ret is None or item is None or item.artisan_id != p.id:
        raise AppError(404, "return_not_found")
    if ret.status != "requested":
        raise AppError(409, "return_not_open")
    ret.status = "received"
    ret.timeline = [*ret.timeline, {"at": utcnow().isoformat(), "status": "received"}]
    refund = await refund_item(db, item, f"return_{ret.reason}")
    if refund.status in ("processed", "pending"):
        ret.status = "refunded"
        ret.timeline = [*ret.timeline, {"at": utcnow().isoformat(), "status": "refunded"}]
    item.fulfilment_status = "returned"
    unit = await db.get(KaruId, item.karu_id) if item.karu_id else None
    if unit:
        unit.status, unit.current_owner_user_id = "returned", None
        db.add(KaruIdEvent(karu_id=unit.id, event="returned", data={"reason": ret.reason}))
        await sync_quantity(db, await db.get(Listing, unit.listing_id))
    await db.commit()
    return {"status": ret.status, "refund": refund.status}


@router.post("/artisan/karu-ids/{code}/relist")
async def relist_unit(code: str, p: ArtisanProfile = Depends(current_artisan), db: AsyncSession = Depends(get_db)):
    """A returned unit can be offered again: `returned` → `available` (F8)."""
    from app.modules.catalog.service import sync_quantity

    unit = (await db.execute(select(KaruId).where(KaruId.code == code.upper()))).scalar_one_or_none()
    if unit is None or unit.artisan_id != p.id:
        raise AppError(404, "karu_id_not_found")
    if unit.status != "returned":
        raise AppError(409, "not_returned")
    unit.status, unit.sold_at, unit.owned_since, unit.sold_city, unit.order_item_id = "available", None, None, None, None
    db.add(KaruIdEvent(karu_id=unit.id, event="relisted", data={}))
    await sync_quantity(db, await db.get(Listing, unit.listing_id))
    await db.commit()
    return {"status": unit.status}
