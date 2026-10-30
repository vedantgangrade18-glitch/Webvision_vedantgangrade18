from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import ratelimit
from app.core.db import get_db
from app.core.deps import ip_hash, optional_user
from app.modules.admin.models import Report

router = APIRouter(tags=["reports"])


class ReportIn(BaseModel):
    target_type: str = Field(pattern="^(listing|karu_id|user|review)$")
    target_id: str = Field(min_length=1, max_length=64)
    reason: str = Field(pattern="^(suspected_fake|copyright|prohibited|child_labour|wrong_info|other)$")
    details: str | None = Field(default=None, max_length=2000)


@router.post("/reports")
async def create_report(body: ReportIn, request: Request, user=Depends(optional_user), db: AsyncSession = Depends(get_db)):
    """Anyone (logged in or not) can report a listing or Karu ID (Part 1 §10)."""
    await ratelimit.enforce(f"report:{ip_hash(request)}", 10, 3600)
    db.add(Report(reporter_user_id=user.id if user else None, target_type=body.target_type, target_id=body.target_id,
                  reason=body.reason, details=body.details))
    await db.commit()
    return {"ok": True}
