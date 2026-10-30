from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import current_user, locale_dep
from app.core.errors import AppError
from app.modules.artisans.models import ArtisanProfile
from app.modules.artisans.service import evaluate_passport, public_maker
from app.modules.catalog.models import Listing
from app.modules.catalog.service import cards
from app.modules.orders.models import Order, OrderItem
from app.modules.reviews.models import Follow, Review, Wishlist

router = APIRouter(tags=["reviews"])


class ReviewIn(BaseModel):
    order_item_id: str
    rating: int = Field(ge=1, le=5)
    text: str | None = Field(default=None, max_length=2000)
    photo_media_ids: list[str] = Field(default_factory=list, max_length=4)


@router.post("/reviews")
async def create_review(body: ReviewIn, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    """Only verified purchasers, once per order item, after delivery (Part 1 §4.2). Feeds L2 records."""
    from app.modules.media.service import owned_media

    item = await db.get(OrderItem, uuid.UUID(body.order_item_id))
    order = await db.get(Order, item.order_id) if item else None
    if item is None or order is None or order.buyer_user_id != user.id:
        raise AppError(404, "order_item_not_found")
    if item.fulfilment_status not in ("delivered", "return_requested", "returned"):
        raise AppError(409, "not_delivered_yet")
    if (await db.execute(select(Review.id).where(Review.order_item_id == item.id))).first():
        raise AppError(409, "already_reviewed")
    photos = [str((await owned_media(db, m, user.id, {"photo"})).id) for m in body.photo_media_ids]
    db.add(Review(order_item_id=item.id, buyer_user_id=user.id, listing_id=item.listing_id, artisan_id=item.artisan_id,
                  rating=body.rating, text=(body.text or "").strip() or None, photos=photos))
    await db.flush()
    listing = await db.get(Listing, item.listing_id)
    cnt, avg = (await db.execute(select(func.count(), func.avg(Review.rating)).where(
        Review.listing_id == listing.id, Review.status == "published"))).one()
    listing.rating_count, listing.rating_avg = cnt, float(avg) if avg is not None else None
    await evaluate_passport(db, await db.get(ArtisanProfile, item.artisan_id))
    await db.commit()
    return {"ok": True}


@router.get("/me/reviews")
async def my_reviews(user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    from app.core.i18n import pick_lang

    rows = (await db.execute(select(Review, Listing).join(Listing, Listing.id == Review.listing_id)
                             .where(Review.buyer_user_id == user.id).order_by(desc(Review.created_at)))).all()
    return {"items": [{"id": str(r.id), "rating": r.rating, "text": r.text, "product": pick_lang(li.title, "en")[0],
                       "code": li.short_code, "created_at": r.created_at.isoformat()} for r, li in rows]}


@router.get("/wishlist")
async def wishlist(locale: str = Depends(locale_dep), user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Listing).join(Wishlist, Wishlist.listing_id == Listing.id)
                             .where(Wishlist.user_id == user.id, Listing.status.in_(["published", "paused"]))
                             .order_by(desc(Wishlist.created_at)))).scalars().all()
    return {"items": await cards(db, list(rows), locale, user.id)}


@router.post("/wishlist/{listing_id}")
async def add_wish(listing_id: str, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    lid = uuid.UUID(listing_id)
    if await db.get(Listing, lid) is None:
        raise AppError(404, "product_not_found")
    if not (await db.execute(select(Wishlist.id).where(Wishlist.user_id == user.id, Wishlist.listing_id == lid))).first():
        db.add(Wishlist(user_id=user.id, listing_id=lid))
        await db.commit()
    return {"wishlisted": True}


@router.delete("/wishlist/{listing_id}")
async def remove_wish(listing_id: str, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(Wishlist).where(Wishlist.user_id == user.id,
                                                   Wishlist.listing_id == uuid.UUID(listing_id)))).scalar_one_or_none()
    if row:
        await db.delete(row)
        await db.commit()
    return {"wishlisted": False}


@router.get("/following")
async def following(locale: str = Depends(locale_dep), user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(ArtisanProfile).join(Follow, Follow.artisan_id == ArtisanProfile.id)
                             .where(Follow.user_id == user.id).order_by(desc(Follow.created_at)))).scalars().all()
    return {"items": [await public_maker(db, p, locale) for p in rows]}


@router.post("/follows/{artisan_id}")
async def follow(artisan_id: str, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    aid = uuid.UUID(artisan_id)
    p = await db.get(ArtisanProfile, aid)
    if p is None:
        raise AppError(404, "maker_not_found")
    if p.user_id == user.id:
        raise AppError(409, "cannot_follow_self")
    if not (await db.execute(select(Follow.id).where(Follow.user_id == user.id, Follow.artisan_id == aid))).first():
        db.add(Follow(user_id=user.id, artisan_id=aid))
        await db.commit()
    return {"following": True}


@router.delete("/follows/{artisan_id}")
async def unfollow(artisan_id: str, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(Follow).where(Follow.user_id == user.id,
                                                 Follow.artisan_id == uuid.UUID(artisan_id)))).scalar_one_or_none()
    if row:
        await db.delete(row)
        await db.commit()
    return {"following": False}
