"""End-to-end: F1 onboarding → F2 Snap + Speak → F3 verification → F4 purchase → payout → F5 proof page."""

from datetime import timedelta

import pytest
from sqlalchemy import update

from app.core import jobs
from app.core.db import sessionmaker, utcnow
from tests.conftest import FAKE_MP4, FAKE_WEBM, become_artisan, login, textured_jpeg, upload

TRANSCRIPT = ("यह भागलपुरी सूती साड़ी है, हथकरघा पर बुनी है, प्राकृतिक नील से रंगी है। "
              "इसे बनाने में 3 दिन लगे। लंबाई 5.5 मीटर है। कीमत 1800 रुपये।")


@pytest.mark.asyncio
async def test_full_marketplace_flow(make_client, monkeypatch):
    from app.modules.ai_pipeline import service as ai
    from app.providers.imagegen import FakeImageGen

    class SafetyBlocksPeople(FakeImageGen):  # the saree "worn" shot is refused; its no-person fallback must land
        async def edit(self, prompt, images, **kw):
            if "Indian model" in prompt:
                raise RuntimeError("blocked")
            return await super().edit(prompt, images, **kw)

    monkeypatch.setattr(ai, "get_imagegen", SafetyBlocksPeople)
    artisan = await make_client()
    me = await login(artisan, "9876543210")
    assert me["is_new"] and me["user"]["roles"] == ["buyer"]
    enabled = await become_artisan(artisan)
    assert enabled["passport_code"].startswith("KRP-")

    # F2: photos + voice note → draft
    photos = [await upload(artisan, "photo", textured_jpeg(i), "image/jpeg") for i in (1, 2)]
    voice = await upload(artisan, "voice", FAKE_WEBM, "audio/webm", duration_s=12)
    r = await artisan.post("/api/v1/listings", json={"photo_media_ids": photos, "voice_media_id": voice,
                                                     "client_transcript": TRANSCRIPT, "source_lang": "hi"})
    assert r.status_code == 200, r.text
    lid, job_id = r.json()["listing_id"], r.json()["job_id"]
    await jobs.drain()
    job = (await artisan.get(f"/api/v1/jobs/{job_id}")).json()
    assert job["status"] == "completed", job
    li = (await artisan.get(f"/api/v1/listings/{lid}")).json()
    assert li["status"] == "draft"
    assert li["price_inr"] == 1800
    assert li["category_slug"] == "sarees"
    assert li["attributes"]["material"] == "cotton"
    assert li["attributes"]["dye"] == "natural indigo"
    assert li["attributes"]["time_to_make_days"] == 3
    assert li["missing_fields"] == []  # computed from the saree specs, not the LLM: no dye/technique warnings
    assert {"hi", "en"} <= set(li["title"]) and li["description"]["hi"]
    # 5 AI catalogue shots and real photos
    ai_shots = [g for g in li["gallery"] if g.get("ai")]
    assert len(ai_shots) == 5
    real_photos = [g for g in li["gallery"] if not g.get("ai")]
    assert len(real_photos) == 2
    assert all(g["enhanced"] for g in real_photos)
    assert li["gallery"][0]["ai"] is True
    assert li["gallery"][0]["is_primary"] is True

    # DELETE one shot leaves 4
    del_target = ai_shots[-1]["id"]
    del_res = await artisan.delete(f"/api/v1/listings/{lid}/shots/{del_target}")
    assert del_res.status_code == 200, del_res.text
    li = (await artisan.get(f"/api/v1/listings/{lid}")).json()
    ai_shots_after = [g for g in li["gallery"] if g.get("ai")]
    assert len(ai_shots_after) == 4

    advice = (await artisan.get(f"/api/v1/listings/{lid}/price-advice")).json()
    assert advice["status"] in ("fresh", "insufficient")
    assert advice["handmade"] and advice["replica"]
    assert advice["basis"] == "replica"  # not verified yet → replica level + comparison
    assert advice["compare_message"]
    assert len(advice["sources"]) >= 3

    # Publish 3 units → 3 Karu IDs; verification without a video → not verified + tips
    r = await artisan.post(f"/api/v1/listings/{lid}/publish", json={"quantity": 3, "returnable": True})
    assert r.status_code == 200, r.text
    pub = r.json()
    assert len(pub["karu_ids"]) == 3 and pub["verification_status"] == "checking"
    await jobs.drain()
    ver = (await artisan.get(f"/api/v1/listings/{lid}/verification")).json()
    assert ver["status"] == "not_verified"
    assert any(t["key"] == "tip.add_video" for t in ver["run"]["tips"])
    assert "score" not in str(ver["run"]).lower()  # artisans never see numbers

    # F3: add a making video → verified
    vid = await upload(artisan, "video", FAKE_MP4, "video/mp4", duration_s=45)
    r = await artisan.post(f"/api/v1/listings/{lid}/making-video", json={"media_id": vid})
    assert r.status_code == 200 and r.json()["verification_status"] == "checking"
    await jobs.drain()
    ver = (await artisan.get(f"/api/v1/listings/{lid}/verification")).json()
    assert ver["status"] == "verified", ver
    advice = (await artisan.get(f"/api/v1/listings/{lid}/price-advice")).json()
    assert advice["basis"] == "handmade"

    # Share image + tags PDF
    share = (await artisan.post(f"/api/v1/listings/{lid}/share-image", json={"format": "4x5"})).json()
    assert share["image_url"].endswith(".jpg") and "karu.test/p/" in share["caption"]
    pdf = await artisan.get(f"/api/v1/listings/{lid}/tags.pdf")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")

    # Public product + proof (buyers see checks, never numbers)
    code = pub["short_code"]
    anon = await make_client()
    prod = (await anon.get(f"/api/v1/catalog/products/{code}")).json()
    assert prod["verification"]["status"] == "verified"
    assert prod["gallery"][0]["ai"] is True
    assert any(not g.get("ai") for g in prod["gallery"])
    assert {c["key"] for c in prod["verification"]["checks"]} == {"handmade_look", "maker_record", "making_video"}
    assert prod["verification"]["checks"][1]["state"] == "new_maker"
    assert "l1" not in str(prod["verification"]).lower()
    hits = (await anon.get("/api/v1/catalog/search", params={"q": "bhagalpuri saree"})).json()
    assert any(i["code"] == code for i in hits["items"])
    hits = (await anon.get("/api/v1/catalog/search", params={"q": "साड़ी"})).json()
    assert any(i["code"] == code for i in hits["items"])

    # F4: buyer purchase (fake test checkout)
    buyer = await make_client()
    await login(buyer, "9123456780", "en")
    addr = (await buyer.post("/api/v1/addresses", json={"name": "Asha Mehta", "phone": "9123456780", "line1": "12 MG Road",
                                                         "city": "Pune", "state": "Maharashtra", "pin": "411001"})).json()
    r = await buyer.post("/api/v1/cart/items", json={"listing_id": lid, "qty": 1})
    assert r.status_code == 200 and r.json()["count"] == 1
    r = await buyer.post("/api/v1/orders", json={"address_id": addr["id"]}, headers={"Idempotency-Key": "test-order-1"})
    assert r.status_code == 200, r.text
    order = r.json()
    assert order["provider"] == "fake" and order["amount_paise"] == 180000
    r = await buyer.post(f"/api/v1/orders/{order['order_id']}/payment/fake-complete", json={"method": "upi"})
    assert r.status_code == 200 and r.json()["status"] == "paid"
    await jobs.drain()
    o = (await buyer.get(f"/api/v1/orders/{order['order_id']}")).json()
    item = o["items"][0]
    assert item["status"] == "to_pack" and item["karu_id"] in pub["karu_ids"]
    li = (await artisan.get(f"/api/v1/listings/{lid}")).json()
    assert li["quantity_available"] == 2

    # Payout waits for setup, then goes on hold
    pay = (await artisan.get("/api/v1/artisan/payouts")).json()
    assert pay["items"][0]["status"] == "awaiting_account"
    r = await artisan.post("/api/v1/artisan/payouts/setup", json={"method": "bank", "account_number": "123456789012",
                                                                  "ifsc": "SBIN0001234"})
    assert r.json()["payout_status"] == "active"
    pay = (await artisan.get("/api/v1/artisan/payouts")).json()
    assert pay["items"][0]["status"] == "on_hold"

    # Ship → buyer confirms → return window → release
    orders = (await artisan.get("/api/v1/artisan/orders", params={"status": "to_pack"})).json()
    assert orders["items"][0]["buyer"] == {"first_name": "Asha", "city": "Pune"}
    r = await artisan.post(f"/api/v1/artisan/orders/items/{item['id']}/ship", json={"courier": "India Post", "tracking_no": "EE123"})
    assert r.status_code == 200
    r = await buyer.post(f"/api/v1/orders/{order['order_id']}/items/{item['id']}/received")
    assert r.json()["items"][0]["status"] == "delivered" and r.json()["items"][0]["can_return"]

    from app.modules.orders.models import OrderItem
    from app.modules.payments.service import release_holds

    async with sessionmaker()() as db:
        await db.execute(update(OrderItem).values(delivered_at=utcnow() - timedelta(days=8),
                                                  return_window_ends_at=utcnow() - timedelta(days=1)))
        await db.commit()
        await release_holds(db)
        await db.commit()
    await jobs.drain()
    pay = (await artisan.get("/api/v1/artisan/payouts")).json()
    assert pay["items"][0]["status"] == "released"
    assert pay["totals"]["paid_inr"] == 1800

    # Review → F5 proof page for the sold unit (owned by buyer)
    r = await buyer.post("/api/v1/reviews", json={"order_item_id": item["id"], "rating": 5, "text": "Beautiful weave"})
    assert r.status_code == 200, r.text
    kid = (await buyer.get(f"/api/v1/karu-ids/{item['karu_id']}")).json()
    assert kid["verdict"] == "verified" and kid["sold"] and kid["owned_by_viewer"]
    assert [j["event"] for j in kid["journey"]][:3] == ["made", "listed", "sold"]
    kid_anon = (await anon.get(f"/api/v1/karu-ids/{item['karu_id'].lower()}")).json()
    assert kid_anon["owned_by_viewer"] is False and kid_anon["sold_on"]
    assert "phone" not in str(kid_anon) and "Pune" in str(kid_anon["journey"])  # city only


@pytest.mark.asyncio
async def test_last_unit_race_and_listing_without_voice(make_client):
    seller = await make_client()
    await login(seller, "9000000001")
    await become_artisan(seller, "Meena Devi", ["madhubani"])
    photo = await upload(seller, "photo", textured_jpeg(7), "image/jpeg")
    r = await seller.post("/api/v1/listings", json={"photo_media_ids": [photo]})
    lid = r.json()["listing_id"]
    await jobs.drain()
    li = (await seller.get(f"/api/v1/listings/{lid}")).json()
    assert li["price_inr"] is None and "price_inr" in li["missing_fields"]  # asked via number pad
    r = await seller.post(f"/api/v1/listings/{lid}/publish", json={"quantity": 1, "returnable": False})
    assert r.status_code == 400 and r.json()["error"]["code"] == "listing_incomplete"
    await seller.patch(f"/api/v1/listings/{lid}", json={"price_inr": 2500, "category_slug": "paintings",
                                                        "title": {"en": "Madhubani fish painting"}})
    li = (await seller.get(f"/api/v1/listings/{lid}")).json()
    assert li["missing_fields"] == ["material", "dimensions.height_cm"]  # recomputed for the new category
    r = await seller.post(f"/api/v1/listings/{lid}/publish", json={"quantity": 1, "returnable": False})
    assert r.status_code == 200, r.text
    await jobs.drain()

    b1, b2 = await make_client(), await make_client()
    for c, phone in ((b1, "9111111111"), (b2, "9222222222")):
        await login(c, phone, "en")
    ids = []
    for c in (b1, b2):
        a = (await c.post("/api/v1/addresses", json={"name": "Buyer", "phone": "9111111111", "line1": "1 Street",
                                                     "city": "Delhi", "state": "Delhi", "pin": "110001"})).json()
        ids.append(a["id"])
    r1 = await b1.post("/api/v1/orders", json={"address_id": ids[0], "buy_now": {"listing_id": lid, "qty": 1}})
    assert r1.status_code == 200
    r2 = await b2.post("/api/v1/orders", json={"address_id": ids[1], "buy_now": {"listing_id": lid, "qty": 1}})
    assert r2.status_code == 409 and r2.json()["error"]["code"] == "just_sold_out"

    # Request this again on the now out-of-stock piece (F7)
    r = await b2.post(f"/api/v1/listings/{lid}/make-again", json={"quantity": 2, "note": "For my sister's wedding"})
    assert r.status_code == 200
    await jobs.drain()
    reqs = (await seller.get("/api/v1/artisan/requests")).json()
    assert reqs["items"][0]["quantity"] == 2
    r = await seller.post(f"/api/v1/artisan/requests/{reqs['items'][0]['id']}/reply",
                          json={"action": "reply", "price_inr": 2600, "ready_in_days": 10})
    assert r.json()["status"] == "replied"
