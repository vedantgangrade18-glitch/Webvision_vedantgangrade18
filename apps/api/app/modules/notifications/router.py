from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db, utcnow
from app.core.deps import current_user
from app.modules.notifications.models import Notification

router = APIRouter(tags=["notifications"])


@router.get("/me/notifications")
async def list_notifications(limit: int = 30, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Notification).where(Notification.user_id == user.id, Notification.channel == "in_app")
                             .order_by(desc(Notification.created_at)).limit(min(limit, 100)))).scalars().all()
    unread = (await db.execute(select(func.count()).select_from(Notification).where(
        Notification.user_id == user.id, Notification.channel == "in_app", Notification.read_at.is_(None)))).scalar_one()
    return {
        "unread": unread,
        "items": [{"id": str(n.id), "type": n.type, "body": n.body, "link": n.link, "created_at": n.created_at.isoformat(),
                   "read": n.read_at is not None} for n in rows],
    }


class ReadIn(BaseModel):
    ids: list[str] | None = None


@router.post("/me/notifications/read")
async def mark_read(body: ReadIn, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    q = update(Notification).where(Notification.user_id == user.id, Notification.channel == "in_app",
                                   Notification.read_at.is_(None))
    if body.ids:
        import uuid

        q = q.where(Notification.id.in_([uuid.UUID(i) for i in body.ids]))
    await db.execute(q.values(read_at=utcnow(), status="read"))
    await db.commit()
    return {"ok": True}
