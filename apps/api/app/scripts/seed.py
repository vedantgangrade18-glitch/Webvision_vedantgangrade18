"""Demo seed (Part 1 §13): 7 makers in 4 clusters, 21 products, a buyer with an order + review,
and a staff account. Everything goes through the real API with the fake providers, so the
AI pipeline, pricing and verification engine produce the data.

Product photos and maker portraits are authentic handcrafted craft photographs
(4:5 aspect ratio, textured weave/brushwork, real Indian artisans) loaded from
seed_assets with procedural fallback; making videos remain demo placeholder files.

    python -m app.scripts.seed            # fake AI/web providers: fast and deterministic (~1 min)
    python -m app.scripts.seed --live     # use the configured Gemini/TinyFish keys (slower, real prices)
"""

from __future__ import annotations

import asyncio
import io
import os
import random
import shutil
import sys
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageFilter

from app.core import jobs
from app.core.config import get_settings
from app.core.imaging import hamming, phash

MAKERS = [
    {"phone": "9999900001", "name": "Ramesh Kumar", "locale": "hi", "crafts": ["bhagalpuri-silk"], "village": "Nathnagar",
     "district": "Bhagalpur", "state": "Bihar", "pin": "812006", "years": 22, "aadhaar": True, "pehchan": True,
     "story": {"hi": "मेरे दादा भी करघा चलाते थे। मैं बाईस साल से टसर और सूती साड़ियाँ बुन रहा हूँ।",
               "en": "My grandfather worked the loom too. I have been weaving tussar and cotton sarees for 22 years."}},
    {"phone": "9999900002", "name": "Sunita Devi", "locale": "hi", "crafts": ["bhagalpuri-silk"], "village": "Champanagar",
     "district": "Bhagalpur", "state": "Bihar", "pin": "812004", "years": 15, "aadhaar": True, "pehchan": False,
     "story": {"hi": "मैं अपने घर के करघे पर दुपट्टे और साड़ियाँ बुनती हूँ।",
               "en": "I weave dupattas and sarees on the loom at home."}},
    {"phone": "9999900003", "name": "Meena Jha", "locale": "hi", "crafts": ["madhubani"], "village": "Jitwarpur",
     "district": "Madhubani", "state": "Bihar", "pin": "847211", "years": 18, "aadhaar": True, "pehchan": False,
     "story": {"hi": "माँ से मधुबनी चित्रकला सीखी। मैं प्रकृति और लोककथाओं के चित्र बनाती हूँ।",
               "en": "I learnt Madhubani painting from my mother. I paint nature and folk stories."}},
    {"phone": "9999900004", "name": "Pooja Kumari", "locale": "hi", "crafts": ["madhubani"], "village": "Ranti",
     "district": "Madhubani", "state": "Bihar", "pin": "847211", "years": 6, "aadhaar": False, "pehchan": False,
     "story": {"hi": "मैं नई पीढ़ी की चित्रकार हूँ और पुराने रूपांकनों को नए तरीके से बनाती हूँ।",
               "en": "I am a young painter giving old motifs a new life."}},
    {"phone": "9999900005", "name": "Kanta Ben", "locale": "gu", "crafts": ["kutch-embroidery"], "village": "Hodka",
     "district": "Kutch", "state": "Gujarat", "pin": "370510", "years": 30, "aadhaar": True, "pehchan": False,
     "story": {"gu": "હું ત્રીસ વર્ષથી કચ્છી ભરતકામ કરું છું.", "en": "I have done Kutch embroidery for thirty years."}},
    {"phone": "9999900006", "name": "Ramila Ben", "locale": "gu", "crafts": ["kutch-embroidery"], "village": "Bhujodi",
     "district": "Kutch", "state": "Gujarat", "pin": "370020", "years": 12, "aadhaar": False, "pehchan": False,
     "story": {"gu": "અરીસા કામ મારી ખાસિયત છે.", "en": "Mirror work is my speciality."}},
    {"phone": "9999900007", "name": "Salim Qureshi", "locale": "ur", "crafts": ["khurja-pottery"], "village": "Khurja",
     "district": "Bulandshahr", "state": "Uttar Pradesh", "pin": "203131", "years": 25, "aadhaar": True, "pehchan": False,
     "story": {"ur": "ہمارا خاندان تین نسلوں سے خورجہ میں برتن بنا رہا ہے۔",
               "en": "Our family has made pottery in Khurja for three generations."}},
]

# (maker index, style, transcript in maker's language, quantity, with_video)
PRODUCTS = [
    (0, "saree", "यह भागलपुरी सूती साड़ी है, हथकरघा पर बुनी है, प्राकृतिक नील से रंगी है। इसे बनाने में 3 दिन लगे। लंबाई 5.5 मीटर है। कीमत 1800 रुपये।", 3, True),
    (0, "saree", "यह भागलपुरी टसर सिल्क साड़ी है, हथकरघा पर बुनी है। इसे बनाने में 7 दिन लगे। लंबाई 5.5 मीटर है। कीमत 4200 रुपये।", 2, True),
    (0, "saree", "यह सूती साड़ी है, हथकरघा पर बुनी, लाल और सफ़ेद रंग। इसे बनाने में 4 दिन लगे। कीमत 2100 रुपये।", 1, True),
    (0, "dupatta", "यह टसर सिल्क दुपट्टा है, हथकरघा पर बुना है। इसे बनाने में 2 दिन लगे। कीमत 1200 रुपये।", 4, False),
    (1, "dupatta", "यह सूती दुपट्टा है, हथकरघा पर बुना, प्राकृतिक नील रंग। इसे बनाने में 2 दिन लगे। कीमत 900 रुपये।", 5, True),
    (1, "saree", "यह सूती साड़ी है, हथकरघा पर बुनी, पीला और हरा रंग। इसे बनाने में 5 दिन लगे। कीमत 2400 रुपये।", 2, False),
    (1, "fabric", "यह सूती कपड़ा है, हथकरघा पर बुना, कुर्ते के लिए। इसे बनाने में 3 दिन लगे। लंबाई 2.5 मीटर। कीमत 1100 रुपये।", 6, True),
    (2, "painting", "यह मधुबनी चित्र है, हाथ से पेंट किया, मछली और कमल। इसे बनाने में 6 दिन लगे। कीमत 3500 रुपये।", 1, True),
    (2, "painting", "यह मधुबनी चित्र है, हाथ से पेंट किया, पेड़ और पक्षी। इसे बनाने में 8 दिन लगे। कीमत 4800 रुपये।", 1, True),
    (2, "painting", "यह मधुबनी चित्र है, हाथ से पेंट किया, सूरज। इसे बनाने में 3 दिन लगे। कीमत 1600 रुपये।", 2, False),
    (3, "painting", "यह मधुबनी चित्र है, हाथ से पेंट किया, हाथी। इसे बनाने में 4 दिन लगे। कीमत 2200 रुपये।", 1, True),
    (3, "painting", "यह मधुबनी चित्र है, हाथ से पेंट किया, मोर। इसे बनाने में 5 दिन लगे। कीमत 2700 रुपये।", 1, False),
    (4, "embroidery", "This is a cotton dupatta with hand embroidery and mirror work, red and black. It took 12 days. Price 3200 rupees.", 2, True),
    (4, "embroidery", "This is a cushion cover with hand embroidery, red and orange. It took 5 days. Price 1400 rupees.", 4, True),
    (4, "embroidery", "This is a wall hanging with hand embroidery and mirror work. It took 9 days. Price 2600 rupees.", 1, False),
    (5, "embroidery", "This is a cotton stole with hand embroidery, blue and white. It took 6 days. Price 1900 rupees.", 3, True),
    (5, "embroidery", "This is a cushion cover with hand embroidery and mirror work. It took 4 days. Price 1200 rupees.", 2, False),
    (6, "pottery", "This is a wheel thrown terracotta pot with blue glaze. It took 3 days. Height 25 cm. Price 850 rupees.", 5, True),
    (6, "pottery", "This is a wheel thrown pottery vase with blue and brown glaze. It took 4 days. Price 1250 rupees.", 3, True),
    (6, "pottery", "This is a set of wheel thrown clay diya, hand painted. It took 2 days. Price 450 rupees.", 8, False),
    (6, "pottery", "This is a wheel thrown terracotta planter. It took 3 days. Price 700 rupees.", 4, True),
]

PALETTES = {
    "saree": [((31, 42, 107), (240, 232, 214)), ((150, 30, 40), (245, 236, 220)), ((200, 160, 40), (60, 110, 70)),
              ((120, 40, 90), (230, 190, 90))],
    "dupatta": [((60, 80, 160), (235, 228, 210)), ((190, 120, 40), (250, 240, 220))],
    "fabric": [((40, 90, 130), (235, 230, 220))],
    "painting": [((180, 40, 40), (245, 225, 170)), ((30, 30, 30), (240, 220, 180)), ((40, 110, 60), (245, 230, 190))],
    "embroidery": [((160, 20, 30), (20, 20, 20)), ((30, 60, 140), (240, 240, 230)), ((200, 80, 20), (250, 200, 60))],
    "pottery": [((40, 80, 160), (150, 90, 50)), ((170, 90, 50), (60, 40, 30)), ((120, 60, 40), (230, 200, 160))],
}


def _bg(rnd: random.Random) -> tuple[int, int, int]:
    return tuple(rnd.randint(218, 238) for _ in range(3))  # plain, light background


def draw_product(style: str, seed: int) -> bytes:
    rnd = random.Random(seed)
    W, H = 1000, 1250
    img = Image.new("RGB", (W, H), _bg(rnd))
    d = ImageDraw.Draw(img)
    a, b = rnd.choice(PALETTES[style])
    if style in ("saree", "dupatta", "fabric"):
        x0, y0 = rnd.randint(90, 180), rnd.randint(110, 200)
        x1, y1 = W - rnd.randint(90, 180), H - rnd.randint(110, 200)
        d.rectangle([x0, y0, x1, y1], fill=b)
        stripe = rnd.randint(8, 22)
        for y in range(y0, y1, stripe * 2):
            jitter = rnd.randint(-2, 2)
            d.rectangle([x0, y + jitter, x1, y + stripe + jitter], fill=a)
        border = rnd.randint(40, 90)
        d.rectangle([x0, y1 - border, x1, y1], fill=a)
        for x in range(x0 + 10, x1 - 10, rnd.randint(28, 46)):
            d.polygon([(x, y1 - border + 10), (x + 14, y1 - 12), (x - 14, y1 - 12)], fill=b)
        for _ in range(rnd.randint(2500, 4000)):  # slubs / weave irregularity
            x, y = rnd.randint(x0, x1), rnd.randint(y0, y1)
            c = tuple(max(0, min(255, v + rnd.randint(-35, 35))) for v in img.getpixel((x, y)))
            d.line([(x, y), (x + rnd.randint(2, 7), y)], fill=c)
    elif style == "painting":
        m = rnd.randint(70, 130)
        d.rectangle([m, m, W - m, H - m], fill=b, outline=a, width=rnd.randint(10, 20))
        for _ in range(rnd.randint(3, 6)):
            cx, cy, r = rnd.randint(250, W - 250), rnd.randint(300, H - 300), rnd.randint(70, 180)
            d.ellipse([cx - r, cy - r // 2, cx + r, cy + r // 2], outline=a, width=6)
            for k in range(-r + 12, r - 12, 12):
                d.line([(cx + k, cy - r // 3), (cx + k + 6, cy + r // 3)], fill=a, width=2)
        for _ in range(rnd.randint(30, 60)):
            x, y = rnd.randint(m + 20, W - m - 40), rnd.randint(m + 20, H - m - 40)
            d.arc([x, y, x + 30, y + 30], rnd.randint(0, 180), rnd.randint(180, 360), fill=a, width=3)
    elif style == "embroidery":
        m = rnd.randint(90, 150)
        d.rectangle([m, m, W - m, H - m], fill=a)
        step = rnd.randint(55, 85)
        for y in range(m + 40, H - m - 40, step):
            for x in range(m + 40, W - m - 40, step):
                r = rnd.randint(14, 22)
                d.regular_polygon((x, y, r), rnd.choice([4, 6, 8]), rotation=rnd.randint(0, 45), outline=b, width=4)
                d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(225, 225, 230))  # mirrors
    else:  # pottery
        cx = W // 2 + rnd.randint(-40, 40)
        top, bottom = rnd.randint(220, 330), H - rnd.randint(170, 260)
        widths = [rnd.randint(140, 220), rnd.randint(260, 380), rnd.randint(150, 230)]
        pts_l, pts_r = [], []
        for i in range(41):
            t = i / 40
            w = widths[0] * (1 - t) ** 2 + 2 * widths[1] * t * (1 - t) + widths[2] * t ** 2
            y = top + t * (bottom - top)
            pts_l.append((cx - w, y))
            pts_r.append((cx + w, y))
        d.polygon(pts_l + pts_r[::-1], fill=b)
        glaze_end = top + (bottom - top) * rnd.uniform(0.35, 0.6)
        d.polygon([p for p in pts_l if p[1] <= glaze_end] + [p for p in pts_r if p[1] <= glaze_end][::-1], fill=a)
        for k in range(8):  # wheel marks
            y = top + (k + 1) * (bottom - top) / 9 + rnd.randint(-6, 6)
            d.line([(cx - widths[1] * 0.9, y), (cx + widths[1] * 0.9, y)], fill=tuple(max(0, v - 25) for v in b), width=2)
        d.ellipse([cx - widths[0], top - 25, cx + widths[0], top + 25], fill=tuple(max(0, v - 40) for v in a))
    img = img.filter(ImageFilter.GaussianBlur(0.6))
    # gentle vignette so photos read as photos, not flat graphics
    shade = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(shade)
    for i in range(0, 120, 4):
        sd.rectangle([i, i, W - i, H - i], outline=int(40 * (1 - i / 120)))
    img = Image.composite(Image.new("RGB", (W, H), (120, 110, 100)), img, shade)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=88)
    return buf.getvalue()


PLACEHOLDER_VIDEO = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2" + b"\x00" * 8192


class Seeder:
    def __init__(self, client: httpx.AsyncClient):
        self.c = client
        self.sessions: dict[str, httpx.Cookies] = {}

    async def req(self, method: str, url: str, **kw) -> httpx.Response:
        headers = kw.pop("headers", {})
        csrf = self.c.cookies.get("karu_csrf")
        if csrf and method in ("POST", "PUT", "PATCH", "DELETE"):
            headers["X-CSRF-Token"] = csrf
        r = await self.c.request(method, url, headers=headers, **kw)
        if r.status_code >= 400:
            raise RuntimeError(f"{method} {url} → {r.status_code} {r.text[:300]}")
        return r

    async def login(self, phone: str, locale: str) -> dict:
        """OTP login once per persona; later switches reuse the saved session cookies."""
        self.c.cookies.clear()
        if phone in self.sessions:
            self.c.cookies.update(self.sessions[phone])
            await self.req("POST", "/api/v1/auth/refresh")
            return (await self.req("GET", "/api/v1/me")).json()
        code = (await self.req("POST", "/api/v1/auth/otp/send", json={"phone": phone, "locale": locale})).json()["dev_code"]
        out = (await self.req("POST", "/api/v1/auth/otp/verify", json={"phone": phone, "code": code, "locale": locale})).json()
        self.sessions[phone] = httpx.Cookies(self.c.cookies)
        return out

    async def upload(self, kind: str, data: bytes, mime: str, duration: float | None = None) -> str:
        r = (await self.req("POST", "/api/v1/media/uploads", json={"kind": kind, "mime": mime, "bytes": len(data),
                                                                   "duration_s": duration})).json()
        size, parts = r["part_size"], []
        for p in r["parts"]:
            n = p["part_number"]
            url = p["url"].split("/api/v1", 1)[1]
            pr = await self.req("PUT", "/api/v1" + url, content=data[(n - 1) * size:n * size])
            parts.append({"part_number": n, "etag": pr.headers.get("etag")})
        return (await self.req("POST", f"/api/v1/media/uploads/{r['media_id']}/complete",
                               json={"parts": parts, "duration_s": duration})).json()["id"]


ASSETS_DIR = Path(__file__).resolve().parent / "seed_assets"
PROD_DIR = ASSETS_DIR / "products"
MAKER_DIR = ASSETS_DIR / "makers"


def get_maker_portrait(mi: int) -> bytes:
    p = MAKER_DIR / f"m{mi}.jpg"
    if p.exists():
        return p.read_bytes()
    return draw_product("painting", 50 + mi)


def get_product_photo(pi: int, k: int, style: str) -> bytes:
    p = PROD_DIR / f"p{pi}_{k}.jpg"
    if p.exists():
        return p.read_bytes()
    return draw_product(style, 1000 + pi * 10 + k)


def unique_photos(count_needed: int) -> list[tuple[str, bytes]]:
    """Load authentic craft photos from seed_assets, with fallback to procedural generation."""
    out: list[tuple[str, bytes, str]] = []
    seed = 1000
    for pi, (_, style, *_rest) in enumerate(PRODUCTS):
        for k in range(2):
            data = get_product_photo(pi, k, style)
            ph = phash(Image.open(io.BytesIO(data)))
            if any(hamming(ph, o[2]) <= 8 for o in out):
                while True:
                    seed += 1
                    data = draw_product(style, seed)
                    ph = phash(Image.open(io.BytesIO(data)))
                    if all(hamming(ph, o[2]) > 8 for o in out):
                        break
            out.append((f"{pi}_{k}", data, ph))
    return [(k, d) for k, d, _ in out]


async def main() -> None:
    s = get_settings()
    if not s.is_dev:
        sys.exit("Seeding is for local/test environments only.")
    from app.main import _bootstrap, create_app
    from app.providers.messaging import messaging_is_fake

    if not messaging_is_fake():
        sys.exit("Seed needs the fake messaging provider (unset SMS/WhatsApp/email keys).")
    if "--reset" in sys.argv:
        var_dir = Path("var")
        db_file = var_dir / "karu.db"
        media_dir = var_dir / "media"
        if db_file.exists():
            db_file.unlink()
        if media_dir.exists():
            shutil.rmtree(media_dir, ignore_errors=True)
        print("Reset existing karu.db and var/media for fresh seed.")
    if "--live" not in sys.argv:
        from app.providers.llm import FakeLLM, set_llm
        from app.providers.stt import FakeSTT, set_stt
        from app.providers.webintel import FakeWebIntel, set_webintel

        set_llm(FakeLLM())
        set_stt(FakeSTT())
        set_webintel(FakeWebIntel())
    await _bootstrap()
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://seed", timeout=120) as client:
        sd = Seeder(client)
        first = await sd.login(MAKERS[0]["phone"], MAKERS[0]["locale"])
        if first["user"]["has_artisan_profile"]:
            print("Already seeded — nothing to do.")
            return
        photos = unique_photos(len(PRODUCTS) * 2)
        handles = []
        for mi, m in enumerate(MAKERS):
            await sd.login(m["phone"], m["locale"])
            await sd.req("POST", "/api/v1/artisan/enable", json={
                "public_name": m["name"], "legal_name": m["name"], "crafts": m["crafts"], "village_town": m["village"],
                "district": m["district"], "state": m["state"], "pin_code": m["pin"], "years_of_practice": m["years"],
                "languages": [m["locale"], "hi"] if m["locale"] != "hi" else ["hi"],
                "consents": ["terms", "privacy", "public_voice"],  # public_video withheld: placeholder videos stay private
            })
            portrait = get_maker_portrait(mi)
            pid = await sd.upload("photo", portrait, "image/jpeg")
            prof = (await sd.req("PATCH", "/api/v1/artisan/profile", json={"story_text": m["story"],
                                                                          "profile_photo_media_id": pid})).json()
            handles.append(prof["handle"])
            if m["aadhaar"]:
                start = (await sd.req("POST", "/api/v1/artisan/kyc/aadhaar/start")).json()["redirect_url"]
                state = start.split("state=")[1]
                await client.get("/api/v1/artisan/kyc/aadhaar/callback",
                                 params={"state": state, "decision": "approve", "name": m["name"], "last4": "4821"})
            await sd.req("POST", "/api/v1/artisan/payouts/setup",
                         json={"method": "bank", "account_number": f"5010{mi:08d}", "ifsc": "SBIN0001234"})
            for pi, (owner, style, transcript, qty, with_video) in enumerate(PRODUCTS):
                if owner != mi:
                    continue
                pics = [await sd.upload("photo", photos[pi * 2 + k][1], "image/jpeg") for k in range(2)]
                draft = (await sd.req("POST", "/api/v1/listings", json={
                    "photo_media_ids": pics, "client_transcript": transcript,
                    "source_lang": "hi" if any("ऀ" <= ch <= "ॿ" for ch in transcript) else "en"})).json()
                await jobs.drain(120)
                lid = draft["listing_id"]
                listing = (await sd.req("GET", f"/api/v1/listings/{lid}")).json()
                patch: dict = {}
                if not listing.get("category_slug"):
                    patch["category_slug"] = {"embroidery": "dupattas-stoles", "pottery": "pottery-terracotta"}.get(style, "other")
                if "cushion" in transcript or "wall hanging" in transcript:
                    patch["category_slug"] = "home-textiles"
                patch["craft_slug"] = m["crafts"][0]
                await sd.req("PATCH", f"/api/v1/listings/{lid}", json=patch)
                await sd.req("POST", f"/api/v1/listings/{lid}/publish", json={"quantity": qty, "returnable": style != "painting"})
                await jobs.drain(120)
                if with_video:
                    vid = await sd.upload("video", PLACEHOLDER_VIDEO + os.urandom(64), "video/mp4", 60)
                    await sd.req("POST", f"/api/v1/listings/{lid}/making-video", json={"media_id": vid})
                    await jobs.drain(120)
            print(f"  maker {m['name']} ({handles[-1]}) seeded")

        # Buyer with one delivered order and a review (gives one maker review history)
        await sd.login("9888800001", "en")
        await sd.req("PATCH", "/api/v1/me", json={"display_name": "Asha Mehta"})
        addr = (await sd.req("POST", "/api/v1/addresses", json={"name": "Asha Mehta", "phone": "9888800001",
                                                                "line1": "12 MG Road", "city": "Pune",
                                                                "state": "Maharashtra", "pin": "411001"})).json()
        res = (await sd.req("GET", "/api/v1/catalog/search", params={"maker": handles[6]})).json()
        code = res["items"][0]["code"]
        prod = (await sd.req("GET", f"/api/v1/catalog/products/{code}")).json()
        order = (await sd.req("POST", "/api/v1/orders", json={"address_id": addr["id"],
                                                              "buy_now": {"listing_id": prod["id"], "qty": 1}})).json()
        await sd.req("POST", f"/api/v1/orders/{order['order_id']}/payment/fake-complete", json={"method": "upi"})
        await jobs.drain(60)
        o = (await sd.req("GET", f"/api/v1/orders/{order['order_id']}")).json()
        item_id = o["items"][0]["id"]
        await sd.login(MAKERS[6]["phone"], MAKERS[6]["locale"])
        await sd.req("POST", f"/api/v1/artisan/orders/items/{item_id}/ship", json={"courier": "India Post", "tracking_no": "EK123456789IN"})
        await sd.login("9888800001", "en")
        await sd.req("POST", f"/api/v1/orders/{order['order_id']}/items/{item_id}/received")
        await sd.req("POST", "/api/v1/reviews", json={"order_item_id": item_id, "rating": 5,
                                                      "text": "The glaze is even more beautiful in person."})

        # Staff account (TOTP printed once)
        from sqlalchemy import select

        from app.core.db import sessionmaker
        from app.modules.auth.models import User

        await sd.login("9777700001", "en")
        async with sessionmaker()() as db:
            u = (await db.execute(select(User).order_by(User.created_at.desc()).limit(1))).scalar_one()
            u.roles, u.display_name, u.email = ["buyer", "admin"], "Karu Admin", "admin@karu.test"
            await db.commit()
        await sd.req("POST", "/api/v1/auth/refresh")
        totp = (await sd.req("POST", "/api/v1/auth/totp/setup")).json()
        import pyotp

        await sd.req("POST", "/api/v1/auth/totp/verify", json={"code": pyotp.TOTP(totp["secret"]).now()})
        await sd.req("PUT", "/api/v1/admin/config/flags", json={"value": {"syndication.demo": True}, "reason": "demo seed"})
        await jobs.drain(60)
    print("\nSeed complete.")
    print("  Artisans (OTP shown in the UI in local mode):", ", ".join(f"+91 {m['phone']}" for m in MAKERS))
    print("  Buyer: +91 9888800001")
    print(f"  Admin: +91 9777700001  ·  TOTP secret: {totp['secret']}  (add to an authenticator app)")
    print("  NOTE: product photos are procedural placeholders; replace with real, permitted photos before demo.")


if __name__ == "__main__":
    os.environ.setdefault("RUN_SCHEDULER", "false")
    asyncio.run(main())
