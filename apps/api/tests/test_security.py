import hashlib
import hmac
import json

import pyotp
import pytest
from sqlalchemy import select

from app.core import jobs
from app.core.db import sessionmaker
from tests.conftest import become_artisan, login, textured_jpeg, upload


@pytest.mark.asyncio
async def test_artisan_cannot_touch_another_artisans_listing(make_client):
    a, b = await make_client(), await make_client()
    await login(a, "9300000001")
    await become_artisan(a, "Artisan A")
    await login(b, "9300000002")
    await become_artisan(b, "Artisan B")
    photo = await upload(a, "photo", textured_jpeg(21), "image/jpeg")
    lid = (await a.post("/api/v1/listings", json={"photo_media_ids": [photo]})).json()["listing_id"]
    await jobs.drain()
    assert (await b.get(f"/api/v1/listings/{lid}")).status_code == 404
    assert (await b.patch(f"/api/v1/listings/{lid}", json={"price_inr": 1})).status_code == 404
    assert (await b.delete(f"/api/v1/listings/{lid}")).status_code == 404
    # B cannot attach A's media either
    r = await b.post("/api/v1/listings", json={"photo_media_ids": [photo]})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_csrf_required_for_cookie_auth_mutations(make_client):
    c = await make_client()
    await login(c, "9300000003")
    raw = await c.patch("/api/v1/me", json={"locale": "ur"}, headers={"X-CSRF-Token": "wrong"})
    assert raw.status_code == 403 and raw.json()["error"]["code"] == "csrf_failed"
    ok = await c.patch("/api/v1/me", json={"locale": "ur"})
    assert ok.status_code == 200 and ok.json()["locale"] == "ur"


@pytest.mark.asyncio
async def test_otp_wrong_code_and_attempt_limit(make_client):
    c = await make_client()
    r = await c.post("/api/v1/auth/otp/send", json={"phone": "+91 93000 00004"})
    assert r.status_code == 200
    for _i in range(5):
        bad = await c.post("/api/v1/auth/otp/verify", json={"phone": "9300000004", "code": "000000" if r.json()["dev_code"] != "000000" else "111111"})
        assert bad.status_code == 400
    locked = await c.post("/api/v1/auth/otp/verify", json={"phone": "9300000004", "code": r.json()["dev_code"]})
    assert locked.status_code == 429
    assert (await c.post("/api/v1/auth/otp/send", json={"phone": "12345"})).status_code == 400


@pytest.mark.asyncio
async def test_refresh_rotation_and_reuse_detection(make_client):
    c = await make_client()
    await login(c, "9300000005")
    old = c.cookies.get("karu_rt", path="/api/v1/auth")
    r = await c.post("/api/v1/auth/refresh")
    assert r.status_code == 200
    c2 = await make_client()
    c2.cookies.set("karu_rt", old, path="/api/v1/auth")
    reuse = await c2.post("/api/v1/auth/refresh")
    assert reuse.status_code == 401 and reuse.json()["error"]["code"] == "refresh_token_reused"


@pytest.mark.asyncio
async def test_webhook_signature_and_idempotency(make_client):
    from app.providers.payments import FakePayments, get_payments

    c = await make_client()
    body = json.dumps({"event": "payment.failed", "payload": {}}).encode()
    bad = await c.post("/api/v1/webhooks/razorpay", content=body, headers={"x-razorpay-signature": "nope"})
    assert bad.status_code == 400
    provider = get_payments()
    assert isinstance(provider, FakePayments)
    sig = hmac.new(provider.secret.encode(), body, hashlib.sha256).hexdigest()
    h = {"x-razorpay-signature": sig, "x-razorpay-event-id": "evt_1"}
    assert (await c.post("/api/v1/webhooks/razorpay", content=body, headers=h)).json() == {"ok": True}
    assert (await c.post("/api/v1/webhooks/razorpay", content=body, headers=h)).json()["duplicate"] is True


@pytest.mark.asyncio
async def test_admin_requires_staff_role_and_totp(make_client):
    from app.modules.auth.models import User

    c = await make_client()
    await login(c, "9300000006")
    assert (await c.get("/api/v1/admin/metrics")).status_code == 403
    async with sessionmaker()() as db:
        u = (await db.execute(select(User).order_by(User.created_at.desc()).limit(1))).scalar_one()
        u.roles = ["buyer", "admin"]
        await db.commit()
    await c.post("/api/v1/auth/refresh")  # new access token carries the role
    r = await c.get("/api/v1/admin/metrics")
    assert r.status_code == 403 and r.json()["error"]["code"] == "totp_required"
    secret = (await c.post("/api/v1/auth/totp/setup")).json()["secret"]
    assert (await c.post("/api/v1/auth/totp/verify", json={"code": pyotp.TOTP(secret).now()})).status_code == 200
    r = await c.get("/api/v1/admin/metrics")
    assert r.status_code == 200, r.text
    # Config validation: weights must sum to 1, and changes are audited
    bad = await c.put("/api/v1/admin/config/verification.v1", json={"value": {"weights": {"L1": 0.5, "L2": 0.5, "L3": 0.5}},
                                                                     "reason": "test"})
    assert bad.status_code == 400
    ok = await c.put("/api/v1/admin/config/verification.v1", json={"value": {"threshold": 72}, "reason": "tuning"})
    assert ok.status_code == 200 and ok.json()["value"]["threshold"] == 72
    log = (await c.get("/api/v1/admin/audit-log")).json()
    assert any(e["action"] == "config.update" for e in log["items"])
    await c.put("/api/v1/admin/config/verification.v1", json={"value": {"threshold": 70}, "reason": "reset"})


@pytest.mark.asyncio
async def test_uploads_reject_wrong_types(make_client):
    c = await make_client()
    await login(c, "9300000007")
    r = await c.post("/api/v1/media/direct", data={"kind": "photo"}, files={"file": ("x.jpg", b"<?php evil ?>", "image/jpeg")})
    assert r.status_code == 400 and r.json()["error"]["code"] == "unsupported_media_type"
    big = await c.post("/api/v1/media/uploads", json={"kind": "video", "mime": "video/mp4", "bytes": 400 * 1024 * 1024})
    assert big.status_code == 400
