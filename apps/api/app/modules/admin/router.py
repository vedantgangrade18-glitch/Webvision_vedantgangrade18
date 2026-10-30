"""Staff console API (S01–S08). Every write is audited; staff need TOTP 2FA."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import case, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import appconfig
from app.core.audit import audit
from app.core.db import get_db, utcnow
from app.core.deps import ip_hash, require_staff
from app.core.errors import AppError, bad_request
from app.core.i18n import format_inr, pick_lang
from app.core.security import decrypt, hmac_hash
from app.modules.admin.models import AuditLog, ExternalCall, Report
from app.modules.artisans.models import ArtisanProfile, Passport
from app.modules.auth.models import User
from app.modules.catalog.models import Category, Listing
from app.modules.catalog.service import primary_images
from app.modules.orders.models import Order
from app.modules.payments.models import Transfer
from app.modules.requests.models import BulkOpportunity, BulkRequest, BulkResponse
from app.modules.verification.models import ImageMatch, VerificationLayerResult, VerificationRun

router = APIRouter(prefix="/admin", tags=["admin"])

any_staff = require_staff()
admin_only = require_staff("admin")
moderation = require_staff("moderator")
ops = require_staff("ops")


def _num(v) -> float:
    return float(v or 0)


@router.get("/metrics")
async def metrics(staff=Depends(any_staff), db: AsyncSession = Depends(get_db)):
    now = utcnow()
    week = now - timedelta(days=7)
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month = day.replace(day=1)
    users = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    users_7d = (await db.execute(select(func.count()).select_from(User).where(User.created_at >= week))).scalar_one()
    artisans = (await db.execute(select(func.count()).select_from(ArtisanProfile))).scalar_one()
    published = (await db.execute(select(func.count()).select_from(Listing).where(Listing.status == "published"))).scalar_one()
    runs = dict((await db.execute(select(VerificationRun.verdict, func.count()).where(VerificationRun.status == "completed",
                                                                                      VerificationRun.triggered_by != "periodic")
                                  .group_by(VerificationRun.verdict))).all())
    total_runs = sum(runs.values())
    gmv = (await db.execute(select(func.coalesce(func.sum(Order.total), 0)).where(
        Order.status.in_(["paid", "partially_shipped", "completed"])))).scalar_one()
    pending_payouts = (await db.execute(select(func.coalesce(func.sum(Transfer.amount), 0)).where(
        Transfer.status.in_(["awaiting_account", "created", "on_hold"])))).scalar_one()

    async def cost(provider: str, since: datetime) -> float:
        return _num((await db.execute(select(func.coalesce(func.sum(ExternalCall.cost_inr), 0)).where(
            ExternalCall.provider == provider, ExternalCall.at >= since))).scalar_one())

    async def calls(provider: str, since: datetime) -> int:
        return (await db.execute(select(func.count()).select_from(ExternalCall).where(
            ExternalCall.provider == provider, ExternalCall.at >= since))).scalar_one()

    open_reports = (await db.execute(select(func.count()).select_from(Report).where(Report.status == "open"))).scalar_one()
    return {
        "signups": {"total": users, "last_7d": users_7d, "artisans": artisans},
        "listings": {"published": published},
        "verification": {"completed": total_runs, "verified": runs.get("verified", 0),
                         "pass_rate": round(runs.get("verified", 0) / total_runs, 3) if total_runs else None},
        "gmv_inr": _num(gmv), "gmv": format_inr(gmv),
        "payouts_pending_inr": _num(pending_payouts), "payouts_pending": format_inr(pending_payouts),
        "tinyfish": {"calls_today": await calls("tinyfish", day), "cost_today_inr": await cost("tinyfish", day),
                     "cost_month_inr": await cost("tinyfish", month)},
        "gemini": {"calls_today": await calls("gemini", day), "cost_today_inr": await cost("gemini", day),
                   "cost_month_inr": await cost("gemini", month)},
        "open_reports": open_reports,
    }


# ---- S02 users --------------------------------------------------------------------------------------------


@router.get("/users")
async def users(q: str | None = None, role: str | None = None, staff=Depends(any_staff), db: AsyncSession = Depends(get_db)):
    stmt = select(User, ArtisanProfile).outerjoin(ArtisanProfile, ArtisanProfile.user_id == User.id)
    if q:
        like = f"%{q.lower()}%"
        conds = [func.lower(User.display_name).like(like), func.lower(User.email).like(like),
                 func.lower(ArtisanProfile.public_name).like(like), ArtisanProfile.handle.like(like)]
        digits = "".join(ch for ch in q if ch.isdigit() or ch == "+")
        if len(digits) >= 10:
            from app.modules.auth.service import normalise_phone

            try:
                conds.append(User.phone_hash == hmac_hash(normalise_phone(digits), "phone"))
            except AppError:
                pass
        stmt = stmt.where(or_(*conds))
    rows = (await db.execute(stmt.order_by(desc(User.created_at)).limit(100))).all()
    out = []
    for u, p in rows:
        if role and role not in u.roles:
            continue
        passport = (await db.execute(select(Passport).where(Passport.artisan_id == p.id))).scalar_one_or_none() if p else None
        out.append({"id": str(u.id), "display_name": u.display_name, "email": u.email, "roles": u.roles, "status": u.status,
                    "created_at": u.created_at.isoformat(), "locale": u.locale,
                    "artisan": {"id": str(p.id), "public_name": p.public_name, "handle": p.handle, "district": p.district,
                                "state": p.state, "aadhaar": p.aadhaar_status, "pehchan": p.pehchan_status,
                                "payout": p.payout_status,
                                "passport": {"id": str(passport.id), "code": passport.passport_code, "state": passport.state}
                                if passport else None} if p else None})
    return {"items": out}


class ReasonIn(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


@router.post("/users/{user_id}/suspend")
async def suspend(user_id: str, body: ReasonIn, request: Request, staff=Depends(moderation), db: AsyncSession = Depends(get_db)):
    from app.modules.auth.service import revoke_all

    u = await db.get(User, uuid.UUID(user_id))
    if u is None:
        raise AppError(404, "user_not_found")
    if set(u.roles) & {"admin"} and "admin" not in staff.roles:
        raise AppError(403, "cannot_suspend_admin")
    before = {"status": u.status}
    u.status = "suspended"
    await revoke_all(db, u.id)
    p = (await db.execute(select(ArtisanProfile).where(ArtisanProfile.user_id == u.id))).scalar_one_or_none()
    if p:
        passport = (await db.execute(select(Passport).where(Passport.artisan_id == p.id))).scalar_one()
        passport.state, passport.suspended_at, passport.state_reason = "suspended", utcnow(), body.reason
        await db.execute(Transfer.__table__.update().where(Transfer.artisan_id == p.id, Transfer.status == "on_hold")
                         .values(failure_reason="held: account under review"))
    await audit(db, staff.id, "user.suspend", "user", str(u.id), before, {"status": "suspended"}, body.reason, ip_hash(request))
    await db.commit()
    return {"status": u.status}


@router.post("/users/{user_id}/restore")
async def restore(user_id: str, body: ReasonIn, request: Request, staff=Depends(moderation), db: AsyncSession = Depends(get_db)):
    from app.modules.artisans.service import evaluate_passport

    u = await db.get(User, uuid.UUID(user_id))
    if u is None:
        raise AppError(404, "user_not_found")
    u.status = "active"
    p = (await db.execute(select(ArtisanProfile).where(ArtisanProfile.user_id == u.id))).scalar_one_or_none()
    if p:
        passport = (await db.execute(select(Passport).where(Passport.artisan_id == p.id))).scalar_one()
        passport.state, passport.state_reason, passport.staff_override = "unverified", body.reason, False
        await evaluate_passport(db, p)
    await audit(db, staff.id, "user.restore", "user", str(u.id), {"status": "suspended"}, {"status": "active"}, body.reason,
                ip_hash(request))
    await db.commit()
    return {"status": u.status}


class PassportStateIn(BaseModel):
    state: str = Field(pattern="^(unverified|verified|suspended)$")
    reason: str = Field(min_length=3, max_length=500)


@router.post("/passports/{passport_id}/state")
async def passport_state(passport_id: str, body: PassportStateIn, request: Request, staff=Depends(admin_only),
                         db: AsyncSession = Depends(get_db)):
    pp = await db.get(Passport, uuid.UUID(passport_id))
    if pp is None:
        raise AppError(404, "passport_not_found")
    before = {"state": pp.state}
    pp.state, pp.state_reason, pp.staff_override = body.state, body.reason, True
    if body.state == "verified":
        pp.verified_at = utcnow()
    if body.state == "suspended":
        pp.suspended_at = utcnow()
    await audit(db, staff.id, "passport.override", "passport", str(pp.id), before, {"state": body.state}, body.reason,
                ip_hash(request))
    await db.commit()
    return {"state": pp.state}


# ---- S03 listings & verification ------------------------------------------------------------------------------------


@router.get("/listings")
async def listings(q: str | None = None, status: str | None = None, verification: str | None = None,
                   staff=Depends(any_staff), db: AsyncSession = Depends(get_db)):
    stmt = select(Listing, ArtisanProfile).join(ArtisanProfile, ArtisanProfile.id == Listing.artisan_id)
    if status:
        stmt = stmt.where(Listing.status == status)
    if verification:
        stmt = stmt.where(Listing.verification_status == verification)
    if q:
        stmt = stmt.where(or_(Listing.search_text.like(f"%{q.lower()}%"), Listing.short_code == q.upper()))
    rows = (await db.execute(stmt.order_by(desc(Listing.updated_at)).limit(200))).all()
    images = await primary_images(db, [li.id for li, _ in rows])
    out = []
    for li, p in rows:
        run = await db.get(VerificationRun, li.current_verification_run_id) if li.current_verification_run_id else None
        out.append({"id": str(li.id), "code": li.short_code, "title": pick_lang(li.title, "en")[0], "status": li.status,
                    "hidden": li.hidden_by_staff, "verification": li.verification_status, "image": images.get(li.id),
                    "maker": {"name": p.public_name, "handle": p.handle}, "price_inr": _num(li.price_inr),
                    "run": {"id": str(run.id), "score": run.karu_score, "l1": run.l1_score, "l2": run.l2_score,
                            "l3": run.l3_score, "hard_fail": run.hard_fail, "status": run.status} if run else None})
    return {"items": out}


async def _listing(db: AsyncSession, listing_id: str) -> Listing:
    li = await db.get(Listing, uuid.UUID(listing_id))
    if li is None:
        raise AppError(404, "listing_not_found")
    return li


@router.post("/listings/{listing_id}/hide")
async def hide(listing_id: str, body: ReasonIn, request: Request, staff=Depends(moderation), db: AsyncSession = Depends(get_db)):
    from app.core.revalidate import revalidate_listing

    li = await _listing(db, listing_id)
    li.hidden_by_staff = True
    await audit(db, staff.id, "listing.hide", "listing", str(li.id), {"hidden": False}, {"hidden": True}, body.reason, ip_hash(request))
    await db.commit()
    await revalidate_listing(db, li)
    return {"hidden": True}


@router.post("/listings/{listing_id}/unhide")
async def unhide(listing_id: str, body: ReasonIn, request: Request, staff=Depends(moderation), db: AsyncSession = Depends(get_db)):
    from app.core.revalidate import revalidate_listing

    li = await _listing(db, listing_id)
    li.hidden_by_staff = False
    await audit(db, staff.id, "listing.unhide", "listing", str(li.id), {"hidden": True}, {"hidden": False}, body.reason, ip_hash(request))
    await db.commit()
    await revalidate_listing(db, li)
    return {"hidden": False}


@router.get("/listings/{listing_id}/runs")
async def listing_runs(listing_id: str, staff=Depends(any_staff), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(VerificationRun).where(VerificationRun.listing_id == uuid.UUID(listing_id))
                             .order_by(desc(VerificationRun.created_at)))).scalars().all()
    return {"items": [_run_summary(r) for r in rows]}


def _run_summary(r: VerificationRun) -> dict:
    return {"id": str(r.id), "listing_id": str(r.listing_id), "version": r.listing_version, "triggered_by": r.triggered_by,
            "status": r.status, "l1": r.l1_score, "l2": r.l2_score, "l3": r.l3_score, "l2_mode": r.l2_mode,
            "karu_score": r.karu_score, "verdict": r.verdict, "hard_fail": r.hard_fail, "hard_fail_reason": r.hard_fail_reason,
            "deferred": r.deferred_checks, "created_at": r.created_at.isoformat(),
            "completed_at": r.completed_at.isoformat() if r.completed_at else None, "error": r.error}


@router.get("/verification-runs/{run_id}")
async def run_detail(run_id: str, staff=Depends(any_staff), db: AsyncSession = Depends(get_db)):
    r = await db.get(VerificationRun, uuid.UUID(run_id))
    if r is None:
        raise AppError(404, "run_not_found")
    layers = (await db.execute(select(VerificationLayerResult).where(VerificationLayerResult.run_id == r.id))).scalars().all()
    matches = (await db.execute(select(ImageMatch).where(ImageMatch.run_id == r.id))).scalars().all()
    return {**_run_summary(r), "config": r.config_snapshot, "tips": r.artisan_tips, "layer_status": r.layer_status,
            "layers": [{"layer": x.layer, "score": x.score, "sub_scores": x.sub_scores, "evidence": x.evidence,
                        "models": x.model_versions} for x in layers],
            "matches": [{"url": m.matched_url, "domain": m.matched_domain, "similarity": m.similarity, "own": m.is_own_channel}
                        for m in matches]}


@router.post("/listings/{listing_id}/revoke-verification")
async def revoke_verification(listing_id: str, body: ReasonIn, request: Request, staff=Depends(moderation),
                              db: AsyncSession = Depends(get_db)):
    from app.modules.verification.engine import revoke

    li = await _listing(db, listing_id)
    if li.verification_status != "verified":
        raise AppError(409, "not_verified")
    await revoke(db, li, body.reason, staff.id)
    await audit(db, staff.id, "verification.revoke", "listing", str(li.id), {"status": "verified"}, {"status": "revoked"},
                body.reason, ip_hash(request))
    await db.commit()
    return {"status": li.verification_status}


@router.get("/verification-queue")
async def verification_queue(staff=Depends(any_staff), db: AsyncSession = Depends(get_db)):
    """Read-only: hard fails and borderline runs (±5 around the threshold)."""
    cfg = await appconfig.get_config(db, "verification.v1")
    th = cfg["threshold"]
    rows = (await db.execute(select(VerificationRun).where(VerificationRun.status == "completed", or_(
        VerificationRun.hard_fail.is_(True), VerificationRun.karu_score.between(th - 5, th + 5)))
        .order_by(desc(VerificationRun.completed_at)).limit(100))).scalars().all()
    return {"items": [_run_summary(r) for r in rows], "threshold": th}


# ---- S04 reports ---------------------------------------------------------------------------------------------------


@router.get("/reports")
async def reports(status: str | None = "open", staff=Depends(moderation), db: AsyncSession = Depends(get_db)):
    stmt = select(Report).order_by(desc(Report.created_at)).limit(200)
    if status:
        stmt = stmt.where(Report.status == status)
    rows = (await db.execute(stmt)).scalars().all()
    return {"items": [{"id": str(r.id), "target_type": r.target_type, "target_id": r.target_id, "reason": r.reason,
                       "details": r.details, "status": r.status, "source": r.source, "created_at": r.created_at.isoformat(),
                       "resolution_note": r.resolution_note} for r in rows]}


class ReportPatch(BaseModel):
    status: str = Field(pattern="^(open|confirmed|dismissed|actioned)$")
    resolution_note: str | None = Field(default=None, max_length=1000)


@router.patch("/reports/{report_id}")
async def update_report(report_id: str, body: ReportPatch, request: Request, staff=Depends(moderation),
                        db: AsyncSession = Depends(get_db)):
    r = await db.get(Report, uuid.UUID(report_id))
    if r is None:
        raise AppError(404, "report_not_found")
    before = {"status": r.status}
    r.status, r.resolution_note = body.status, body.resolution_note
    if body.status == "confirmed" and r.reason in ("hard_fail",):
        r.reason = "suspected_fake"  # confirmed fakes count against the maker's L2 record
    await audit(db, staff.id, "report.update", "report", str(r.id), before, {"status": body.status}, body.resolution_note,
                ip_hash(request))
    await db.commit()
    return {"status": r.status}


# ---- S05 bulk requests --------------------------------------------------------------------------------------------------


@router.get("/bulk-requests")
async def bulk_requests(staff=Depends(ops), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(BulkRequest).order_by(desc(BulkRequest.created_at)).limit(200))).scalars().all()
    out = []
    for b in rows:
        cat = await db.get(Category, b.category_id) if b.category_id else None
        opp = (await db.execute(select(BulkOpportunity).where(BulkOpportunity.bulk_request_id == b.id))).scalar_one_or_none()
        responses = []
        if opp:
            for resp, p in (await db.execute(select(BulkResponse, ArtisanProfile).join(ArtisanProfile, ArtisanProfile.id == BulkResponse.artisan_id)
                                             .where(BulkResponse.opportunity_id == opp.id))).all():
                responses.append({"id": str(resp.id), "maker": p.public_name, "handle": p.handle,
                                  "quantity_offered": resp.quantity_offered, "can_meet_deadline": resp.can_meet_deadline,
                                  "note": resp.note, "status": resp.status})
        out.append({"id": str(b.id), "org_name": b.org_name, "contact": json.loads(decrypt(b.contact_enc) or "{}"),
                    "category": cat.slug if cat else None, "product_type": b.product_type, "description": b.description,
                    "quantity": b.quantity, "target_price_inr": _num(b.target_price) if b.target_price else None,
                    "deadline": b.deadline.isoformat() if b.deadline else None, "status": b.status,
                    "created_at": b.created_at.isoformat(), "opportunity_id": str(opp.id) if opp else None,
                    "responses": responses})
    return {"items": out}


@router.post("/bulk-requests/{request_id}/publish")
async def publish_bulk(request_id: str, request: Request, staff=Depends(ops), db: AsyncSession = Depends(get_db)):
    from app.core.i18n import format_date
    from app.modules.notifications.service import notify

    b = await db.get(BulkRequest, uuid.UUID(request_id))
    if b is None:
        raise AppError(404, "bulk_request_not_found")
    if b.status != "new":
        raise AppError(409, "already_published")
    opp = BulkOpportunity(bulk_request_id=b.id, published_at=utcnow(),
                          public_summary={"product_type": b.product_type, "quantity": b.quantity})
    db.add(opp)
    b.status = "published"
    # Notify verified artisans in the category (all verified artisans if no category).
    stmt = select(ArtisanProfile).join(Passport, Passport.artisan_id == ArtisanProfile.id).where(Passport.state == "verified")
    makers = (await db.execute(stmt)).scalars().all()
    notified = 0
    for p in makers:
        if b.category_id:
            has_cat = (await db.execute(select(Listing.id).where(Listing.artisan_id == p.id, Listing.category_id == b.category_id))).first()
            if not has_cat:
                continue
        user = await db.get(User, p.user_id)
        await notify(db, p.user_id, "bulk_opportunity", {"quantity": b.quantity, "product": b.product_type,
                                                         "deadline": format_date(b.deadline, user.locale) if b.deadline else "—"},
                     link="/sell/requests?tab=bulk")
        notified += 1
    await audit(db, staff.id, "bulk.publish", "bulk_request", str(b.id), ip_hash=ip_hash(request))
    await db.commit()
    return {"opportunity_id": str(opp.id), "notified": notified}


@router.post("/bulk-requests/{request_id}/close")
async def close_bulk(request_id: str, request: Request, staff=Depends(ops), db: AsyncSession = Depends(get_db)):
    b = await db.get(BulkRequest, uuid.UUID(request_id))
    if b is None:
        raise AppError(404, "bulk_request_not_found")
    b.status = "closed"
    opp = (await db.execute(select(BulkOpportunity).where(BulkOpportunity.bulk_request_id == b.id))).scalar_one_or_none()
    if opp:
        opp.open, opp.closes_at = False, utcnow()
    await audit(db, staff.id, "bulk.close", "bulk_request", str(b.id), ip_hash=ip_hash(request))
    await db.commit()
    return {"status": "closed"}


class ResponseStatusIn(BaseModel):
    status: str = Field(pattern="^(confirmed|declined|interested)$")


@router.post("/bulk-responses/{response_id}/status")
async def bulk_response_status(response_id: str, body: ResponseStatusIn, request: Request, staff=Depends(ops),
                               db: AsyncSession = Depends(get_db)):
    r = await db.get(BulkResponse, uuid.UUID(response_id))
    if r is None:
        raise AppError(404, "response_not_found")
    r.status = body.status
    await audit(db, staff.id, "bulk.response_status", "bulk_response", str(r.id), after={"status": body.status},
                ip_hash=ip_hash(request))
    await db.commit()
    return {"status": r.status}


# ---- S06 config ------------------------------------------------------------------------------------------------------------


@router.get("/config")
async def config_all(staff=Depends(any_staff), db: AsyncSession = Depends(get_db)):
    return {k: await appconfig.get_config(db, k) for k in appconfig.DEFAULTS}


@router.get("/config/{key}")
async def config_get(key: str, staff=Depends(any_staff), db: AsyncSession = Depends(get_db)):
    if key not in appconfig.DEFAULTS:
        raise AppError(404, "config_not_found")
    return {"key": key, "value": await appconfig.get_config(db, key), "default": appconfig.DEFAULTS[key]}


class ConfigIn(BaseModel):
    value: dict | list
    reason: str = Field(min_length=3, max_length=500)


def _validate_config(key: str, value) -> None:
    if key == "verification.v1":
        merged = appconfig.deep_merge(appconfig.DEFAULTS[key], value)
        w = merged["weights"]
        if abs(sum(w.values()) - 1) > 1e-6 or any(x < 0 for x in w.values()):
            raise bad_request("weights_must_sum_to_1")
        lw = merged["l3"]["weights"]
        if abs(sum(lw.values()) - 1) > 1e-6:
            raise bad_request("l3_weights_must_sum_to_1")
        if not 0 <= merged["threshold"] <= 100 or not 0 <= merged["new_artisan_l2_constant"] <= 100:
            raise bad_request("out_of_range")
    if key == "flags" and not isinstance(value, dict):
        raise bad_request("flags_must_be_object")


@router.put("/config/{key}")
async def config_put(key: str, body: ConfigIn, request: Request, staff=Depends(admin_only), db: AsyncSession = Depends(get_db)):
    from app.modules.admin.models import AppConfig

    if key not in appconfig.DEFAULTS:
        raise AppError(404, "config_not_found")
    _validate_config(key, body.value)
    row = await db.get(AppConfig, key)
    before = row.value if row else None
    if row:
        row.value, row.updated_by = body.value, staff.id
    else:
        db.add(AppConfig(key=key, value=body.value, updated_by=staff.id))
    await audit(db, staff.id, "config.update", "config", key, {"value": before}, {"value": body.value}, body.reason, ip_hash(request))
    await db.commit()
    appconfig.invalidate(key)
    return {"key": key, "value": await appconfig.get_config(db, key)}


class RescoreIn(BaseModel):
    apply: bool = False
    reason: str | None = None


@router.post("/config/verification/rescore")
async def rescore(body: RescoreIn, request: Request, staff=Depends(admin_only), db: AsyncSession = Depends(get_db)):
    """Re-score with current config using stored layer scores — no new AI calls."""
    from app.modules.verification.engine import apply_outcome
    from app.modules.verification.engine import rescore as rescore_run

    cfg = await appconfig.get_config(db, "verification.v1")
    listings_ = (await db.execute(select(Listing).where(Listing.status.in_(["published", "paused"]),
                                                        Listing.current_verification_run_id.is_not(None)))).scalars().all()
    changes = []
    for li in listings_:
        run = await db.get(VerificationRun, li.current_verification_run_id)
        if run is None or run.status != "completed" or run.listing_version != li.version:
            continue
        res = await rescore_run(db, run, cfg)
        if res["old"]["verdict"] != res["new"]["verdict"]:
            changes.append({"listing_id": str(li.id), "code": li.short_code, **res})
            if body.apply:
                run.karu_score, run.verdict = res["new"]["score"], res["new"]["verdict"]
                run.config_snapshot = cfg
                await apply_outcome(db, li, run)
    if body.apply:
        await audit(db, staff.id, "verification.rescore_apply", "config", "verification.v1", after={"changes": len(changes)},
                    reason=body.reason, ip_hash=ip_hash(request))
        await db.commit()
    return {"applied": body.apply, "changes": changes, "evaluated": len(listings_)}


# ---- S07 costs ---------------------------------------------------------------------------------------------------------------


@router.get("/costs")
async def costs(days: int = Query(30, ge=1, le=180), staff=Depends(ops), db: AsyncSession = Depends(get_db)):
    since = utcnow() - timedelta(days=days)
    rows = (await db.execute(select(ExternalCall.provider, ExternalCall.operation, func.count(),
                                    func.coalesce(func.sum(ExternalCall.cost_inr), 0), func.avg(ExternalCall.latency_ms),
                                    func.sum(case((ExternalCall.status == "error", 1), else_=0)))
                             .where(ExternalCall.at >= since).group_by(ExternalCall.provider, ExternalCall.operation))).all()
    calls = (await db.execute(select(ExternalCall.provider, ExternalCall.cost_inr, ExternalCall.at).where(ExternalCall.at >= since))).all()
    daily: dict[str, dict[str, float]] = {}
    for prov, cost, at in calls:
        d = at.date().isoformat()
        daily.setdefault(d, {})
        daily[d][prov] = round(daily[d].get(prov, 0) + float(cost), 4)
    total = sum(float(r[3]) for r in rows)
    listings_n = (await db.execute(select(func.count()).select_from(Listing).where(Listing.published_at >= since))).scalar_one()
    verified_n = (await db.execute(select(func.count()).select_from(VerificationRun).where(
        VerificationRun.completed_at >= since, VerificationRun.verdict == "verified"))).scalar_one()
    budgets = await appconfig.get_config(db, "budgets.v1")
    return {
        "by_operation": [{"provider": r[0], "operation": r[1], "calls": r[2], "cost_inr": round(float(r[3]), 4),
                          "avg_latency_ms": round(float(r[4] or 0)), "errors": int(r[5] or 0)} for r in rows],
        "daily": [{"date": d, **v} for d, v in sorted(daily.items())],
        "total_inr": round(total, 2),
        "per_listing_inr": round(total / listings_n, 2) if listings_n else None,
        "per_verified_inr": round(total / verified_n, 2) if verified_n else None,
        "budgets": budgets,
    }


# ---- S08 audit log ---------------------------------------------------------------------------------------------------------------


@router.get("/audit-log")
async def audit_log(limit: int = Query(100, le=500), staff=Depends(admin_only), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(AuditLog).order_by(desc(AuditLog.at)).limit(limit))).scalars().all()
    actors = {u.id: u for u in (await db.execute(select(User).where(User.id.in_({r.actor_user_id for r in rows if r.actor_user_id})))).scalars()}
    return {"items": [{"id": str(r.id), "at": r.at.isoformat(), "action": r.action, "target_type": r.target_type,
                       "target_id": r.target_id, "reason": r.reason, "before": r.before, "after": r.after,
                       "actor": (actors[r.actor_user_id].display_name or actors[r.actor_user_id].email) if r.actor_user_id in actors else None}
                      for r in rows]}
