"""Test harness: throwaway SQLite DB + local storage, fake providers, in-process jobs."""

from __future__ import annotations

import io
import os
import random
import shutil
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="karu-test-"))
os.environ.update({
    "ENV": "test",
    "DATABASE_URL": f"sqlite+aiosqlite:///{(_TMP / 'test.db').as_posix()}",
    "LOCAL_STORAGE_DIR": str(_TMP / "media"),
    "TASK_MODE": "inline",
    "RUN_SCHEDULER": "false",
    "ADMIN_TOTP_REQUIRED": "true",
    "PUBLIC_BASE_URL": "https://karu.test",
    "API_BASE_URL": "http://test",
    # Force fake providers even if a developer .env holds real keys.
    "OPENAI_API_KEY": "", "GEMINI_API_KEY": "", "VERTEX_PROJECT": "", "TINYFISH_API_KEY": "", "RAZORPAY_KEY_ID": "",
    "RAZORPAY_KEY_SECRET": "", "RAZORPAY_WEBHOOK_SECRET": "", "SMS_PROVIDER_KEY": "", "WHATSAPP_TOKEN": "",
    "EMAIL_API_KEY": "", "GOOGLE_CLIENT_ID": "", "WEB_REVALIDATE_SECRET": "", "REDIS_URL": "", "STORAGE_BACKEND": "local",
})

import httpx  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

from app.core import jobs, ratelimit  # noqa: E402
from app.core.db import Base, get_engine  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _cleanup():
    yield
    shutil.rmtree(_TMP, ignore_errors=True)


@pytest_asyncio.fixture(scope="session")
async def app():
    from app.main import _bootstrap, create_app

    application = create_app()
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _bootstrap()
    yield application
    await jobs.drain(30)


@pytest.fixture(autouse=True)
def _reset_limits():
    ratelimit.reset_memory()


class KaruClient(httpx.AsyncClient):
    """httpx client that echoes the CSRF cookie as X-CSRF-Token (like the web app does)."""

    async def request(self, method, url, **kwargs):  # noqa: ANN001
        headers = dict(kwargs.pop("headers", None) or {})
        csrf = self.cookies.get("karu_csrf")
        if csrf and method.upper() in ("POST", "PUT", "PATCH", "DELETE"):
            headers.setdefault("X-CSRF-Token", csrf)
        return await super().request(method, url, headers=headers, **kwargs)


@pytest_asyncio.fixture
async def make_client(app):
    clients: list[KaruClient] = []

    async def factory() -> KaruClient:
        c = KaruClient(transport=httpx.ASGITransport(app=app), base_url="http://test")
        clients.append(c)
        return c

    yield factory
    for c in clients:
        await c.aclose()


async def login(client: KaruClient, phone: str, locale: str = "hi") -> dict:
    r = await client.post("/api/v1/auth/otp/send", json={"phone": phone, "locale": locale})
    assert r.status_code == 200, r.text
    code = r.json()["dev_code"]
    r = await client.post("/api/v1/auth/otp/verify", json={"phone": phone, "code": code, "locale": locale})
    assert r.status_code == 200, r.text
    return r.json()


def textured_jpeg(seed: int, size: tuple[int, int] = (900, 1100)) -> bytes:
    """A photo-like test image: woven-looking texture that passes the quality gate."""
    rnd = random.Random(seed)
    img = Image.new("RGB", size, (200, 190, 175))
    d = ImageDraw.Draw(img)
    base = (rnd.randint(20, 90), rnd.randint(30, 90), rnd.randint(90, 160))
    for y in range(120, size[1] - 120, 6):
        for x in range(100, size[0] - 100, 6):
            j = rnd.randint(-25, 25)
            d.rectangle([x, y, x + 4, y + 4], fill=(base[0] + j, base[1] + j, base[2] + j))
    for _ in range(40):
        x, y = rnd.randint(120, size[0] - 160), rnd.randint(140, size[1] - 160)
        d.ellipse([x, y, x + 30, y + 30], outline=(230, 180, 60), width=3)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)
    return buf.getvalue()


FAKE_WEBM = b"\x1a\x45\xdf\xa3" + b"\x00" * 2048
FAKE_MP4 = b"\x00\x00\x00\x18ftypisom" + b"\x00" * 4096


async def upload(client: KaruClient, kind: str, data: bytes, mime: str, duration_s: float | None = None) -> str:
    r = await client.post("/api/v1/media/uploads", json={"kind": kind, "mime": mime, "bytes": len(data), "duration_s": duration_s})
    assert r.status_code == 200, r.text
    body = r.json()
    size = body["part_size"]
    parts = []
    for p in body["parts"]:
        n = p["part_number"]
        chunk = data[(n - 1) * size:n * size]
        url = p["url"].replace("http://test", "")
        pr = await client.put(url, content=chunk)
        assert pr.status_code == 200, pr.text
        parts.append({"part_number": n, "etag": pr.headers.get("etag")})
    r = await client.post(f"/api/v1/media/uploads/{body['media_id']}/complete", json={"parts": parts, "duration_s": duration_s})
    assert r.status_code == 200, r.text
    return r.json()["id"]


async def become_artisan(client: KaruClient, name: str = "Ramesh Kumar", crafts: list[str] | None = None) -> dict:
    r = await client.post("/api/v1/artisan/enable", json={
        "public_name": name, "legal_name": name, "crafts": crafts or ["bhagalpuri-silk"], "village_town": "Nathnagar",
        "district": "Bhagalpur", "state": "Bihar", "pin_code": "812006",
        "consents": ["terms", "privacy", "public_voice", "public_video"],
    })
    assert r.status_code == 200, r.text
    return r.json()
