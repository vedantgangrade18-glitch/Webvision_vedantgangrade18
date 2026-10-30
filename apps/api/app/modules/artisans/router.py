from __future__ import annotations

import json
import re
import uuid
from datetime import date

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit
from app.core.config import get_settings
from app.core.db import get_db, utcnow
from app.core.deps import current_artisan, current_user, ip_hash, locale_dep
from app.core.errors import AppError, bad_request
from app.core.i18n import LOCALES, format_inr, pick_lang
from app.core.jobs import enqueue, handler
from app.core.security import create_access_token, decrypt, encrypt
from app.modules.artisans.models import ArtisanProfile
from app.modules.artisans.service import (
    create_passport,
    evaluate_passport,
    get_passport,
    media_url,
    passport_checklist,
    profile_completion,
    public_maker,
    unique_handle,
)
from app.modules.auth.models import Consent, User
from app.modules.auth.service import CONSENT_VERSION, set_session_cookies
from app.providers.kyc import get_kyc
from app.providers.payments import get_payments

router = APIRouter(tags=["artisan"])

STATES = {
    "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh", "goa", "gujarat", "haryana", "himachal pradesh",
    "jharkhand", "karnataka", "kerala", "madhya pradesh", "maharashtra", "manipur", "meghalaya", "mizoram", "nagaland",
    "odisha", "punjab", "rajasthan", "sikkim", "tamil nadu", "telangana", "tripura", "uttar pradesh", "uttarakhand",
    "west bengal", "andaman and nicobar islands", "chandigarh", "dadra and nagar haveli and daman and diu", "delhi",
    "jammu and kashmir", "ladakh", "lakshadweep", "puducherry",
}


class EnableIn(BaseModel):
    public_name: str = Field(min_length=1, max_length=120)
    legal_name: str | None = Field(default=None, max_length=160)
    dob: date | None = None
    crafts: list[str] = Field(default_factory=list, max_length=8)
    village_town: str | None = Field(default=None, max_length=120)
    district: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=64)
    pin_code: str | None = Field(default=None, pattern=r"^\d{6}$")
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    languages: list[str] = Field(default_factory=list)
    years_of_practice: int | None = Field(default=None, ge=0, le=90)
    consents: list[str] = Field(default_factory=list)


def _apply_profile(p: ArtisanProfile, body: BaseModel) -> None:
    data = body.model_dump(exclude_unset=True)
    if "legal_name" in data:
        p.legal_name_enc = encrypt(data["legal_name"]) if data["legal_name"] else None
    if "dob" in data:
        p.dob_enc = encrypt(data["dob"].isoformat()) if data["dob"] else None
        p.dob_year = data["dob"].year if data["dob"] else None
    for key in ("public_name", "village_town", "district", "pin_code", "years_of_practice", "gender",
                "show_voice_publicly"):
        if key in data:
            setattr(p, key, data[key].strip() if isinstance(data[key], str) else data[key])
    if "state" in data:
        st = (data["state"] or "").strip()
        if st and st.lower() not in STATES:
            raise bad_request("invalid_state")
        p.state = st.title() if st else None
    if "crafts" in data:
        p.crafts = [c.strip()[:64] for c in data["crafts"] if c.strip()]
    if "languages" in data:
        p.languages = [x for x in data["languages"] if x in LOCALES]
    if data.get("lat") is not None and data.get("lng") is not None:
        p.lat, p.lng = round(data["lat"], 2), round(data["lng"], 2)  # ~1 km (DPDP minimisation)
    if "story_text" in data and data["story_text"] is not None:
        p.story_text = {k: v.strip()[:2000] for k, v in data["story_text"].items() if k in LOCALES and v and v.strip()}
    if "linked_social_urls" in data and data["linked_social_urls"] is not None:
        p.linked_social_urls = [u.strip()[:255] for u in data["linked_social_urls"] if u.strip()][:8]


@router.post("/artisan/enable")
async def enable(body: EnableIn, request: Request, response: Response, user: User = Depends(current_user),
                 db: AsyncSession = Depends(get_db)):
    """'Start selling': creates the artisan profile and its one Karu Passport (Part 1 §3.1)."""
    if body.dob and body.dob > date.today().replace(year=date.today().year - 18):
        raise bad_request("must_be_adult")
    required = {"terms", "privacy"}
    if not required.issubset(set(body.consents)):
        raise bad_request("consent_required", required=sorted(required))
    existing = (await db.execute(select(ArtisanProfile).where(ArtisanProfile.user_id == user.id))).scalar_one_or_none()
    if existing:
        raise AppError(409, "already_artisan")
    profile = ArtisanProfile(user_id=user.id, public_name=body.public_name.strip(), handle=await unique_handle(db, body.public_name),
                             languages=[user.locale])
    _apply_profile(profile, body)
    profile.onboarding_completed_at = utcnow()
    db.add(profile)
    await db.flush()
    passport = await create_passport(db, profile)
    now = utcnow()
    for c in set(body.consents) & {"terms", "privacy", "public_voice", "public_video", "marketing"}:
        db.add(Consent(user_id=user.id, consent_type=c, version=CONSENT_VERSION, granted_at=now))
    if "artisan" not in user.roles:
        user.roles = [*user.roles, "artisan"]
    user.display_name = user.display_name or profile.public_name
    profile.profile_completion = profile_completion(profile)[0]
    await audit(db, user.id, "artisan.enabled", "artisan", str(profile.id), ip_hash=ip_hash(request))
    await db.commit()
    # Roles changed → refresh the access token (keeps the existing refresh token).
    set_session_cookies(response, create_access_token(str(user.id), user.roles, amr=["otp"]), None)
    return {"artisan_id": str(profile.id), "handle": profile.handle, "passport_code": passport.passport_code}


async def profile_view(db: AsyncSession, p: ArtisanProfile, locale: str) -> dict:
    pct, missing = profile_completion(p)
    from app.core.storage import get_storage
    from app.modules.media.models import Media

    voice = await db.get(Media, p.story_voice_media_id) if p.story_voice_media_id else None
    return {
        "id": str(p.id), "handle": p.handle, "handle_editable": not p.handle_edited, "public_name": p.public_name,
        "legal_name": decrypt(p.legal_name_enc), "dob": decrypt(p.dob_enc), "crafts": p.crafts,
        "years_of_practice": p.years_of_practice, "village_town": p.village_town, "district": p.district, "state": p.state,
        "pin_code": p.pin_code, "languages": p.languages, "story_text": p.story_text,
        "story_voice": {"id": str(voice.id), "url": get_storage().public_url(voice.public_key) if voice.public_key else None}
        if voice else None,
        "show_voice_publicly": p.show_voice_publicly, "photo_url": await media_url(db, p.profile_photo_media_id),
        "linked_social_urls": p.linked_social_urls,
        "aadhaar_status": p.aadhaar_status, "aadhaar_last4": decrypt(p.aadhaar_last4_enc),
        "pehchan_status": p.pehchan_status, "payout_status": p.payout_status, "payout_method": p.payout_method,
        "payout_masked": p.payout_masked, "profile_completion": pct, "profile_missing": missing,
    }


@router.get("/artisan/profile")
async def get_profile(locale: str = Depends(locale_dep), p: ArtisanProfile = Depends(current_artisan),
                      db: AsyncSession = Depends(get_db)):
    return await profile_view(db, p, locale)


class ProfilePatch(BaseModel):
    public_name: str | None = Field(default=None, min_length=1, max_length=120)
    legal_name: str | None = Field(default=None, max_length=160)
    dob: date | None = None
    crafts: list[str] | None = None
    village_town: str | None = None
    district: str | None = None
    state: str | None = None
    pin_code: str | None = Field(default=None, pattern=r"^\d{6}$")
    languages: list[str] | None = None
    years_of_practice: int | None = Field(default=None, ge=0, le=90)
    story_text: dict[str, str] | None = None
    story_voice_media_id: str | None = None
    show_voice_publicly: bool | None = None
    profile_photo_media_id: str | None = None
    linked_social_urls: list[str] | None = None
    handle: str | None = Field(default=None, pattern=r"^[a-z0-9][a-z0-9-]{2,40}$")


@router.patch("/artisan/profile")
async def patch_profile(body: ProfilePatch, locale: str = Depends(locale_dep), user: User = Depends(current_user),
                        p: ArtisanProfile = Depends(current_artisan), db: AsyncSession = Depends(get_db)):
    from app.modules.media.service import owned_media, publish_copy

    _apply_profile(p, body)
    if body.profile_photo_media_id:
        m = await owned_media(db, body.profile_photo_media_id, user.id, {"photo"})
        p.profile_photo_media_id = m.id
    if body.story_voice_media_id:
        m = await owned_media(db, body.story_voice_media_id, user.id, {"voice"})
        p.story_voice_media_id = m.id
    if p.story_voice_media_id and p.show_voice_publicly:
        consent = (await db.execute(select(Consent).where(Consent.user_id == user.id, Consent.consent_type == "public_voice",
                                                          Consent.revoked_at.is_(None)))).first()
        if consent:
            from app.modules.media.models import Media

            await publish_copy(db, await db.get(Media, p.story_voice_media_id))
    if body.handle and body.handle != p.handle:
        if p.handle_edited:
            raise AppError(409, "handle_already_edited")
        if (await db.execute(select(ArtisanProfile.id).where(ArtisanProfile.handle == body.handle))).first():
            raise AppError(409, "handle_taken")
        p.handle, p.handle_edited = body.handle, True
    p.profile_completion = profile_completion(p)[0]
    await db.commit()
    return await profile_view(db, p, locale)


@router.get("/artisan/passport")
async def passport(locale: str = Depends(locale_dep), p: ArtisanProfile = Depends(current_artisan), db: AsyncSession = Depends(get_db)):
    pp = await evaluate_passport(db, p)
    await db.commit()
    return {"passport": {"code": pp.passport_code, "state": pp.state, "verified_at": pp.verified_at.isoformat() if pp.verified_at else None,
                         "member_since": p.created_at.isoformat()},
            "checklist": await passport_checklist(db, p),
            "public": await public_maker(db, p, locale)}


# ---- Aadhaar via DigiLocker (licensed provider) -----------------------------------------------------


@router.post("/artisan/kyc/aadhaar/start")
async def aadhaar_start(p: ArtisanProfile = Depends(current_artisan), db: AsyncSession = Depends(get_db)):
    if p.aadhaar_status == "verified":
        raise AppError(409, "already_verified")
    redirect = f"{get_settings().public_base_url}/sell/passport"
    url = await get_kyc().start(str(p.id), redirect)
    p.aadhaar_status = "pending"
    await db.commit()
    return {"redirect_url": url}


@router.get("/artisan/kyc/aadhaar/fake", response_class=HTMLResponse)
async def aadhaar_fake_page(state: str):
    """Consent page of the FAKE KYC provider (local/staging only). Real DigiLocker replaces this."""
    if get_settings().env == "prod":
        raise AppError(404, "not_found")
    return HTMLResponse(f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Test KYC</title>
<style>body{{font-family:system-ui;background:#FBF8F2;color:#1E1A16;max-width:420px;margin:40px auto;padding:16px}}
.card{{background:#fff;border:1px solid #BDB5AA;border-radius:12px;padding:20px}}
input,button{{font:inherit;width:100%;padding:12px;margin:6px 0;border-radius:8px;border:1px solid #BDB5AA;box-sizing:border-box}}
button{{background:#1F2A6B;color:#fff;border:0}} .muted{{color:#5C554D;font-size:14px}} .warn{{background:#FFF4D6;padding:8px;border-radius:8px}}</style>
</head><body><div class="card"><p class="warn">TEST PROVIDER — no real Aadhaar data is checked or stored.</p>
<h2>DigiLocker consent (test)</h2><p class="muted">Karu will receive only: verified name, last 4 digits and a reference.</p>
<form method="get" action="/api/v1/artisan/kyc/aadhaar/callback">
<input type="hidden" name="state" value="{state}"><label>Name as on Aadhaar<input name="name" required></label>
<label>Last 4 digits<input name="last4" pattern="\\d{{4}}" maxlength="4" required></label>
<button name="decision" value="approve">Allow</button><button name="decision" value="deny" style="background:#7A736B">Deny</button>
</form></div></body></html>""")


@router.get("/artisan/kyc/aadhaar/callback")
async def aadhaar_callback(request: Request, state: str, decision: str = "deny", name: str | None = None,
                           last4: str | None = None, db: AsyncSession = Depends(get_db)):
    import difflib

    from app.core.security import verify_payload
    from app.core.translit import phonetic_key

    try:
        claims = verify_payload(state)
    except Exception:  # noqa: BLE001
        raise AppError(400, "invalid_state") from None
    p = await db.get(ArtisanProfile, uuid.UUID(claims["a"]))
    if p is None:
        raise AppError(404, "artisan_not_found")
    res = await get_kyc().complete({"state": state, "decision": decision, "name": name, "last4": last4})
    if res.status == "verified":
        if last4 and not re.fullmatch(r"\d{4}", res.last4 or ""):
            raise bad_request("invalid_last4")
        legal = decrypt(p.legal_name_enc) or p.public_name
        ratio = difflib.SequenceMatcher(None, phonetic_key(legal or ""), phonetic_key(res.name or "")).ratio() if res.name else 0
        p.aadhaar_status = "verified"
        p.aadhaar_last4_enc = encrypt(res.last4)
        p.aadhaar_verified_at = utcnow()
        p.aadhaar_name_match = ratio >= 0.7
        p.kyc_provider_ref = res.reference
        if not p.legal_name_enc and res.name:
            p.legal_name_enc = encrypt(res.name)
    else:
        p.aadhaar_status = "failed"
    p.profile_completion = profile_completion(p)[0]
    await evaluate_passport(db, p)
    await audit(db, p.user_id, f"kyc.aadhaar.{p.aadhaar_status}", "artisan", str(p.id), ip_hash=ip_hash(request))
    await db.commit()
    return RedirectResponse(f"{claims['r']}?kyc={p.aadhaar_status}", status_code=303)


# ---- Pehchan (DC Handicrafts) via TinyFish Agent --------------------------------------------------------


class PehchanIn(BaseModel):
    card_no: str = Field(min_length=4, max_length=32, pattern=r"^[A-Za-z0-9/\-]+$")


@router.post("/artisan/pehchan")
async def pehchan(body: PehchanIn, user: User = Depends(current_user), p: ArtisanProfile = Depends(current_artisan),
                  db: AsyncSession = Depends(get_db)):
    p.pehchan_card_no_enc = encrypt(body.card_no.upper())
    p.pehchan_status = "pending"
    job = await enqueue(db, "agents.pehchan", ref_type="artisan", ref_id=str(p.id), owner_user_id=user.id)
    await db.commit()
    return {"status": "pending", "job_id": str(job.id)}


@handler("agents.pehchan", queue="agents", max_attempts=6, timeout_s=900)
async def pehchan_job(db: AsyncSession, job) -> dict:
    """Portal has no API and is often slow: retried with backoff; never blocks listing (Part 2 §8.3)."""
    import difflib

    from app.core.translit import phonetic_key
    from app.modules.verification.models import EvidenceItem
    from app.providers.webintel import get_webintel

    p = await db.get(ArtisanProfile, uuid.UUID(job.ref_id))
    web = get_webintel()
    if p is None:
        return {"skipped": True}
    if web.name == "fake":
        p.pehchan_status = "pending"  # no agent available: stay pending, staff can verify manually
        await db.commit()
        return {"status": "pending", "reason": "agent_unavailable"}
    card = decrypt(p.pehchan_card_no_enc)
    result = await web.run_agent(
        "Open the official DC (Handicrafts) artisan/Pehchan card lookup on this site, search for the artisan card "
        "number given in the inputs, and return JSON with keys: found (true/false), name, craft, district, state. "
        "If the site is down or asks for a captcha, return {\"found\": false, \"error\": \"<reason>\"}.",
        start_url=get_settings().pehchan_lookup_url, inputs={"card_number": card},
    )
    data = result.result if isinstance(result.result, dict) else {}
    if isinstance(result.result, str):
        try:
            data = json.loads(result.result)
        except json.JSONDecodeError:
            data = {}
    if result.status != "COMPLETED" or data.get("error"):
        raise RuntimeError(f"pehchan lookup incomplete: {data.get('error') or result.error}")
    legal = decrypt(p.legal_name_enc) or p.public_name
    ratio = difflib.SequenceMatcher(None, phonetic_key(legal), phonetic_key(str(data.get("name") or ""))).ratio()
    p.pehchan_status = "verified" if data.get("found") and ratio >= 0.7 else "failed"
    p.pehchan_checked_at = utcnow()
    ev = EvidenceItem(artisan_id=p.id, kind="registry_screenshot", source_url=get_settings().pehchan_lookup_url,
                      captured_at=utcnow(), summary={"registry": "pehchan", "found": data.get("found"),
                                                     "craft": data.get("craft"), "district": data.get("district"),
                                                     "name_match": round(ratio, 2), "run_id": result.run_id,
                                                     "streaming_url": result.streaming_url})
    db.add(ev)
    await db.flush()
    p.pehchan_evidence_id = ev.id
    await evaluate_passport(db, p)
    await db.commit()
    return {"status": p.pehchan_status}


# ---- Payouts (Razorpay Route linked account) -----------------------------------------------------------------


class PayoutIn(BaseModel):
    method: str = Field(pattern="^(upi|bank)$")
    vpa: str | None = Field(default=None, pattern=r"^[A-Za-z0-9._-]{2,256}@[A-Za-z]{2,64}$")
    account_number: str | None = Field(default=None, pattern=r"^\d{5,35}$")
    ifsc: str | None = Field(default=None, pattern=r"^[A-Z]{4}0[A-Z0-9]{6}$")
    beneficiary_name: str | None = Field(default=None, max_length=120)


@router.post("/artisan/payouts/setup")
async def payout_setup(body: PayoutIn, request: Request, user: User = Depends(current_user),
                       p: ArtisanProfile = Depends(current_artisan), db: AsyncSession = Depends(get_db)):
    if body.method == "upi" and not body.vpa:
        raise bad_request("vpa_required")
    if body.method == "bank" and not (body.account_number and body.ifsc):
        raise bad_request("bank_details_required")
    details = {"vpa": body.vpa} if body.method == "upi" else {
        "account_number": body.account_number, "ifsc": body.ifsc, "beneficiary_name": body.beneficiary_name or p.public_name}
    phone = decrypt(user.phone_enc) or ""
    res = await get_payments().create_linked_account(
        reference_id=p.handle.replace("-", "")[:20], name=decrypt(p.legal_name_enc) or p.public_name,
        email=user.email or f"payouts+{p.handle}@karu.ai", phone=phone,
        address={"village_town": p.village_town, "district": p.district, "state": p.state, "pin_code": p.pin_code},
        method=body.method, details=details,
    )
    p.payout_method = body.method
    p.payout_details_enc = encrypt(json.dumps(details))
    p.payout_masked = body.vpa if body.method == "upi" else f"A/c ••••{body.account_number[-4:]} · {body.ifsc}"
    p.razorpay_linked_account_id = res.account_id
    p.razorpay_product_id = res.product_id
    p.payout_status = res.status
    p.payout_status_reason = res.reason
    p.profile_completion = profile_completion(p)[0]
    await audit(db, user.id, "payout.setup", "artisan", str(p.id), after={"method": body.method, "status": res.status},
                ip_hash=ip_hash(request))
    if res.status == "active":
        from app.modules.payments.service import create_waiting_transfers

        await create_waiting_transfers(db, p)
    await db.commit()
    return {"payout_status": p.payout_status, "payout_masked": p.payout_masked, "reason": p.payout_status_reason}


@router.get("/artisan/payouts")
async def payouts(locale: str = Depends(locale_dep), p: ArtisanProfile = Depends(current_artisan), db: AsyncSession = Depends(get_db)):
    from app.modules.catalog.models import Listing
    from app.modules.orders.models import Order, OrderItem
    from app.modules.payments.models import Transfer

    if p.payout_status == "pending_kyc" and p.razorpay_linked_account_id:
        res = await get_payments().linked_account_status(p.razorpay_linked_account_id, p.razorpay_product_id)
        if res.status != p.payout_status:
            p.payout_status = res.status
            if res.status == "active":
                from app.modules.payments.service import create_waiting_transfers

                await create_waiting_transfers(db, p)
            await db.commit()
    rows = (await db.execute(select(Transfer, OrderItem, Order, Listing).join(OrderItem, OrderItem.id == Transfer.order_item_id)
                             .join(Order, Order.id == OrderItem.order_id).join(Listing, Listing.id == OrderItem.listing_id)
                             .where(Transfer.artisan_id == p.id).order_by(Transfer.created_at.desc()))).all()
    on_way = sum(float(t_.amount) for t_, *_ in rows if t_.status in ("awaiting_account", "created", "on_hold"))
    paid = sum(float(t_.amount) for t_, *_ in rows if t_.status in ("released", "settled"))
    return {
        "setup": {"status": p.payout_status, "method": p.payout_method, "masked": p.payout_masked, "reason": p.payout_status_reason},
        "totals": {"on_the_way_inr": on_way, "paid_inr": paid, "on_the_way": format_inr(on_way), "paid": format_inr(paid)},
        "items": [{"id": str(t_.id), "amount_inr": float(t_.amount), "amount": format_inr(t_.amount), "status": t_.status,
                   "hold_until": t_.hold_until.isoformat() if t_.hold_until else None, "order_number": o.order_number,
                   "title": pick_lang(li.title, locale)[0], "created_at": t_.created_at.isoformat(),
                   "failure_reason": t_.failure_reason} for t_, oi, o, li in rows],
    }


@router.get("/artisan/dashboard")
async def dashboard(locale: str = Depends(locale_dep), p: ArtisanProfile = Depends(current_artisan), db: AsyncSession = Depends(get_db)):
    from app.modules.catalog.models import Listing, ListingMedia
    from app.modules.karu_ids.models import ScanAggregate
    from app.modules.orders.models import OrderItem
    from app.modules.payments.models import Transfer
    from app.modules.requests.models import MakeAgainRequest

    start = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    codes = (await db.execute(select(Listing.short_code).where(Listing.artisan_id == p.id))).scalars().all()
    views_today = 0
    if codes:
        views_today = (await db.execute(select(func.coalesce(func.sum(ScanAggregate.count), 0)).where(
            ScanAggregate.target_type == "view", ScanAggregate.target_code.in_(codes), ScanAggregate.hour >= start))).scalar_one()
    to_ship = (await db.execute(select(func.count()).select_from(OrderItem).where(
        OrderItem.artisan_id == p.id, OrderItem.fulfilment_status == "to_pack"))).scalar_one()
    on_way = (await db.execute(select(func.coalesce(func.sum(Transfer.amount), 0)).where(
        Transfer.artisan_id == p.id, Transfer.status.in_(["awaiting_account", "created", "on_hold"])))).scalar_one()
    awaiting = (await db.execute(select(func.coalesce(func.sum(Transfer.amount), 0)).where(
        Transfer.artisan_id == p.id, Transfer.status == "awaiting_account"))).scalar_one()
    with_video = select(ListingMedia.listing_id).where(ListingMedia.role == "making_video", ListingMedia.active.is_(True))
    need_video = (await db.execute(select(func.count()).select_from(Listing).where(
        Listing.artisan_id == p.id, Listing.status == "published", Listing.verification_status != "verified",
        Listing.id.not_in(with_video)))).scalar_one()
    open_requests = (await db.execute(select(func.count()).select_from(MakeAgainRequest).where(
        MakeAgainRequest.artisan_id == p.id, MakeAgainRequest.status == "open"))).scalar_one()
    banners = []
    if to_ship:
        banners.append({"key": "orders_to_ship", "count": to_ship, "link": "/sell/orders"})
    if need_video:
        banners.append({"key": "add_making_video", "count": need_video, "link": "/sell?filter=not_verified"})
    if float(awaiting) > 0 and p.payout_status != "active":
        banners.append({"key": "finish_payout_setup", "amount": format_inr(awaiting), "link": "/sell/payouts"})
    pct, missing = profile_completion(p)
    passport = await get_passport(db, p.id)
    earned = (await db.execute(select(func.coalesce(func.sum(Transfer.amount), 0)).where(
        Transfer.artisan_id == p.id, Transfer.status.in_(["released", "settled"])))).scalar_one()
    sold = (await db.execute(select(func.count()).select_from(OrderItem).where(
        OrderItem.artisan_id == p.id, OrderItem.fulfilment_status.in_(["to_pack", "shipped", "delivered"])))).scalar_one()
    return {
        "greeting_name": p.public_name,
        "summary": {"views_today": views_today, "orders_to_ship": to_ship, "money_on_the_way_inr": float(on_way),
                    "money_on_the_way": format_inr(on_way)},
        "banners": banners,
        "open_requests": open_requests,
        "profile_completion": pct,
        "profile_missing": missing[:1],
        "passport": {"code": passport.passport_code if passport else None, "state": passport.state if passport else None},
        "impact": {"earned_inr": float(earned), "earned": format_inr(earned), "pieces_sold": sold,
                   "buyer_cities": await _buyer_cities(db, p.id)},
    }


async def _buyer_cities(db: AsyncSession, artisan_id: uuid.UUID) -> int:
    from app.modules.orders.models import Order, OrderItem

    rows = (await db.execute(select(Order.shipping_address).join(OrderItem, OrderItem.order_id == Order.id).where(
        OrderItem.artisan_id == artisan_id, Order.status.in_(["paid", "partially_shipped", "completed"])))).scalars().all()
    return len({(r or {}).get("city", "").strip().lower() for r in rows if (r or {}).get("city")})


_PIN_CACHE: dict[str, dict] = {}


@router.get("/geo/pincode/{pin}")
async def pincode(pin: str, user: User = Depends(current_user)):
    """PIN → district/state for onboarding (India Post public directory), cached in-process."""
    import httpx

    if not re.fullmatch(r"\d{6}", pin):
        raise bad_request("invalid_pin")
    if pin in _PIN_CACHE:
        return _PIN_CACHE[pin]
    out: dict = {"pin": pin, "found": False}
    try:
        async with httpx.AsyncClient(timeout=6) as c:
            r = await c.get(f"https://api.postalpincode.in/pincode/{pin}")
        data = r.json()[0] if r.status_code == 200 else {}
        offices = data.get("PostOffice") or []
        if offices:
            o = offices[0]
            out = {"pin": pin, "found": True, "district": o.get("District"), "state": o.get("State"),
                   "places": sorted({x.get("Name") for x in offices if x.get("Name")})[:20]}
    except Exception:  # noqa: BLE001 - the artisan can always type the place instead
        pass
    _PIN_CACHE[pin] = out
    return out

