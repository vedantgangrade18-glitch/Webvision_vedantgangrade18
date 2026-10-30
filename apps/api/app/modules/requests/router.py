"""'Request this again' (F7) and bulk requests (F9)."""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, time
from decimal import Decimal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import ratelimit
from app.core.db import get_db
from app.core.deps import current_artisan, current_user, ip_hash, locale_dep
from app.core.errors import AppError
from app.core.i18n import IST, format_date, format_inr, pick_lang
from app.core.security import encrypt
from app.modules.artisans.models import ArtisanProfile
from app.modules.catalog.models import Category, Listing
from app.modules.catalog.service import primary_images
from app.modules.requests.models import BulkOpportunity, BulkRequest, BulkResponse, MakeAgainRequest

router = APIRouter(tags=["requests"])


class MakeAgainIn(BaseModel):
    quantity: int = Field(default=1, ge=1, le=500)
    needed_by: date | None = None
    note: str | None = Field(default=None, max_length=1000)


@router.post("/listings/{listing_id}/make-again")
async def make_again(listing_id: str, body: MakeAgainIn, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    from app.modules.notifications.service import notify

    await ratelimit.enforce(f"makeagain:{user.id}", 10, 3600)
    li = await db.get(Listing, uuid.UUID(listing_id))
    if li is None or li.status not in ("published", "paused"):
        raise AppError(404, "product_not_found")
    profile = await db.get(ArtisanProfile, li.artisan_id)
    if profile.user_id == user.id:
        raise AppError(409, "own_listing")
    if body.needed_by and body.needed_by < date.today():
        raise AppError(400, "date_in_past")
    req = MakeAgainRequest(listing_id=li.id, buyer_user_id=user.id, artisan_id=li.artisan_id, quantity=body.quantity,
                           needed_by=body.needed_by, note=(body.note or "").strip() or None)
    db.add(req)
    title = (li.title or {}).get(li.source_lang) or next(iter(li.title.values()), "")
    await notify(db, profile.user_id, "make_again_received", {"title": title, "quantity": body.quantity},
                 link="/sell/requests")
    await db.commit()
    return {"id": str(req.id), "status": req.status}


@router.get("/me/requests")
async def my_requests(locale: str = Depends(locale_dep), user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(MakeAgainRequest, Listing).join(Listing, Listing.id == MakeAgainRequest.listing_id)
                             .where(MakeAgainRequest.buyer_user_id == user.id).order_by(desc(MakeAgainRequest.created_at)))).all()
    return {"items": [{"id": str(r.id), "title": pick_lang(li.title, locale)[0], "code": li.short_code, "quantity": r.quantity,
                       "needed_by": r.needed_by.isoformat() if r.needed_by else None, "status": r.status,
                       "reply": r.artisan_reply, "created_at": r.created_at.isoformat()} for r, li in rows]}


@router.get("/artisan/requests")
async def artisan_requests(locale: str = Depends(locale_dep), p: ArtisanProfile = Depends(current_artisan),
                           db: AsyncSession = Depends(get_db)):
    from app.modules.auth.models import User

    rows = (await db.execute(select(MakeAgainRequest, Listing, User).join(Listing, Listing.id == MakeAgainRequest.listing_id)
                             .join(User, User.id == MakeAgainRequest.buyer_user_id)
                             .where(MakeAgainRequest.artisan_id == p.id).order_by(desc(MakeAgainRequest.created_at)))).all()
    images = await primary_images(db, list({li.id for _, li, _ in rows}))
    return {"items": [{
        "id": str(r.id), "listing_id": str(li.id), "title": pick_lang(li.title, locale)[0], "image": images.get(li.id),
        "quantity": r.quantity, "needed_by": format_date(r.needed_by, locale) if r.needed_by else None, "note": r.note,
        "buyer_first_name": (u.display_name or "").split(" ")[0] or None, "status": r.status, "reply": r.artisan_reply,
        "created_at": r.created_at.isoformat()} for r, li, u in rows]}


class ReplyIn(BaseModel):
    action: str = Field(pattern="^(reply|decline)$")
    price_inr: float | None = Field(default=None, gt=0)
    ready_in_days: int | None = Field(default=None, ge=1, le=365)
    message: str | None = Field(default=None, max_length=1000)


@router.post("/artisan/requests/{request_id}/reply")
async def reply(request_id: str, body: ReplyIn, p: ArtisanProfile = Depends(current_artisan), db: AsyncSession = Depends(get_db)):
    from app.modules.notifications.service import notify

    r = await db.get(MakeAgainRequest, uuid.UUID(request_id))
    if r is None or r.artisan_id != p.id:
        raise AppError(404, "request_not_found")
    if r.status not in ("open", "replied"):
        raise AppError(409, "request_closed")
    li = await db.get(Listing, r.listing_id)
    if body.action == "decline":
        r.status, r.artisan_reply = "declined", {"declined": True, "message": body.message}
        text = body.message or "—"
    else:
        r.status = "replied"
        r.artisan_reply = {"price_inr": body.price_inr, "ready_in_days": body.ready_in_days, "message": body.message}
        bits = [format_inr(body.price_inr) if body.price_inr else None,
                f"{body.ready_in_days} days" if body.ready_in_days else None, body.message]
        text = " · ".join(b for b in bits if b)
    title = pick_lang(li.title, "en")[0]
    await notify(db, r.buyer_user_id, "make_again_answered", {"maker": p.public_name, "title": title, "reply": text},
                 link=f"/p/{li.short_code}", artisan_side=False)
    await db.commit()
    return {"status": r.status}


# ---- Bulk requests -------------------------------------------------------------------------------------------


class BulkIn(BaseModel):
    org_name: str = Field(min_length=2, max_length=160)
    contact_name: str = Field(min_length=2, max_length=120)
    contact_phone: str = Field(min_length=8, max_length=20)
    contact_email: EmailStr
    category_slug: str | None = None
    product_type: str = Field(min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    quantity: int = Field(ge=1, le=1_000_000)
    target_price_inr: float | None = Field(default=None, gt=0)
    deadline: date | None = None


@router.post("/business/bulk-requests")
async def bulk_request(body: BulkIn, request: Request, db: AsyncSession = Depends(get_db)):
    await ratelimit.enforce(f"bulk:{ip_hash(request)}", 5, 3600)
    cat = (await db.execute(select(Category).where(Category.slug == body.category_slug))).scalar_one_or_none() \
        if body.category_slug else None
    br = BulkRequest(org_name=body.org_name.strip(), product_type=body.product_type.strip(), description=body.description,
                     contact_enc=encrypt(json.dumps({"name": body.contact_name, "phone": body.contact_phone,
                                                     "email": body.contact_email})),
                     category_id=cat.id if cat else None, quantity=body.quantity,
                     target_price=Decimal(str(body.target_price_inr)) if body.target_price_inr else None, deadline=body.deadline)
    db.add(br)
    await db.commit()
    return {"id": str(br.id), "status": br.status}


@router.get("/artisan/bulk-opportunities")
async def bulk_opportunities(locale: str = Depends(locale_dep), p: ArtisanProfile = Depends(current_artisan),
                             db: AsyncSession = Depends(get_db)):
    from app.modules.artisans.service import get_passport

    passport = await get_passport(db, p.id)
    rows = (await db.execute(select(BulkOpportunity, BulkRequest).join(BulkRequest, BulkRequest.id == BulkOpportunity.bulk_request_id)
                             .where(BulkOpportunity.open.is_(True)).order_by(desc(BulkOpportunity.published_at)))).all()
    mine = {r.opportunity_id: r for r in (await db.execute(select(BulkResponse).where(BulkResponse.artisan_id == p.id))).scalars()}
    items = []
    for opp, br in rows:
        cat = await db.get(Category, br.category_id) if br.category_id else None
        resp = mine.get(opp.id)
        items.append({"id": str(opp.id), "product_type": br.product_type, "category": pick_lang(cat.name, locale)[0] if cat else None,
                      "quantity": br.quantity, "target_price": format_inr(br.target_price) if br.target_price else None,
                      "deadline": format_date(br.deadline, locale) if br.deadline else None, "description": br.description,
                      "my_response": {"quantity_offered": resp.quantity_offered, "status": resp.status} if resp else None})
    return {"eligible": passport is not None and passport.state == "verified", "items": items}


class BulkRespondIn(BaseModel):
    quantity_offered: int = Field(ge=1, le=1_000_000)
    can_meet_deadline: bool = True
    note: str | None = Field(default=None, max_length=500)


@router.post("/artisan/bulk-opportunities/{opportunity_id}/respond")
async def bulk_respond(opportunity_id: str, body: BulkRespondIn, p: ArtisanProfile = Depends(current_artisan),
                       db: AsyncSession = Depends(get_db)):
    from app.modules.artisans.service import get_passport

    passport = await get_passport(db, p.id)
    if passport is None or passport.state != "verified":
        raise AppError(403, "verified_artisans_only")
    opp = await db.get(BulkOpportunity, uuid.UUID(opportunity_id))
    if opp is None or not opp.open:
        raise AppError(404, "opportunity_not_found")
    existing = (await db.execute(select(BulkResponse).where(BulkResponse.opportunity_id == opp.id,
                                                            BulkResponse.artisan_id == p.id))).scalar_one_or_none()
    if existing:
        existing.quantity_offered, existing.can_meet_deadline, existing.note = body.quantity_offered, body.can_meet_deadline, body.note
    else:
        db.add(BulkResponse(opportunity_id=opp.id, artisan_id=p.id, quantity_offered=body.quantity_offered,
                            can_meet_deadline=body.can_meet_deadline, note=body.note))
    await db.commit()
    return {"ok": True}


def deadline_dt(d: date | None) -> datetime | None:
    return datetime.combine(d, time(23, 59), tzinfo=IST) if d else None
