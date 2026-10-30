"""Web intelligence (TinyFish Search / Fetch / Agent) behind `WebIntel` (Part 2 §8).

TinyFish REST endpoints (docs.tinyfish.ai, checked 2026-10-24), all with `X-API-Key`:
- Search: GET https://api.search.tinyfish.ai?query=…&location=IN&language=en
  → {query, results:[{position, site_name, title, snippet, url, date?}], total_results, page}
- Fetch:  POST https://api.fetch.tinyfish.ai {urls:[≤10], format:"markdown", image_links:true}
  → {results:[{url, final_url, title, description, text, image_links?, published_date?}], errors:[]}
- Agent:  POST https://agent.tinyfish.ai/v1/automation/run-sse {url, goal}
  → SSE events STARTED{run_id} · STREAMING_URL{streaming_url} · PROGRESS{purpose} ·
    HEARTBEAT · COMPLETE{status, result, error}
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Protocol
from urllib.parse import urlparse

import httpx

from app.core.audit import track_call
from app.core.config import get_settings


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str = ""
    site: str = ""
    date: str | None = None


@dataclass
class FetchedPage:
    url: str
    title: str = ""
    text: str = ""
    image_links: list[str] = field(default_factory=list)
    published_date: str | None = None
    error: str | None = None


@dataclass
class AgentStep:
    kind: str  # started|streaming_url|progress|complete
    message: str
    data: dict = field(default_factory=dict)


@dataclass
class AgentResult:
    status: str  # COMPLETED|FAILED|CANCELLED
    result: dict | list | str | None
    run_id: str | None = None
    streaming_url: str | None = None
    error: str | None = None


StepCallback = Callable[[AgentStep], Awaitable[None]]


class WebIntelError(Exception):
    pass


class WebIntel(Protocol):
    name: str

    async def search(self, query: str, *, num: int = 10, region: str = "IN", language: str = "en",
                     listing_id=None, run_id=None) -> list[SearchResult]: ...

    async def fetch(self, urls: list[str], *, image_links: bool = False, listing_id=None, run_id=None) -> list[FetchedPage]: ...

    async def run_agent(self, goal: str, *, start_url: str, inputs: dict | None = None,
                        on_step: StepCallback | None = None, listing_id=None,
                        profile_id: str | None = None) -> AgentResult: ...


def domain_of(url: str) -> str:
    if not url:
        return ""
    if "://" not in url:
        url = "https://" + url
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


class TinyFishWebIntel:
    name = "tinyfish"
    SEARCH_URL = "https://api.search.tinyfish.ai"
    FETCH_URL = "https://api.fetch.tinyfish.ai"
    AGENT_SSE_URL = "https://agent.tinyfish.ai/v1/automation/run-sse"

    def __init__(self, api_key: str):
        self.headers = {"X-API-Key": api_key}

    @staticmethod
    def _cost(op: str) -> float:
        from app.core.appconfig import DEFAULTS

        return DEFAULTS["costs.v1"].get(f"tinyfish.{op}", 0.0)

    async def search(self, query, *, num=10, region="IN", language="en", listing_id=None, run_id=None):
        params = {"query": query, "location": region, "language": language}
        async with track_call("tinyfish", "search", cost_inr=self._cost("search"), listing_id=listing_id, run_id=run_id):
            async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
                resp = await client.get(self.SEARCH_URL, params=params, headers=self.headers)
            if resp.status_code >= 400:
                raise WebIntelError(f"tinyfish search {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        out = []
        for r in (data.get("results") or [])[:num]:
            if not r.get("url"):
                continue
            out.append(SearchResult(title=r.get("title") or "", url=r["url"], snippet=r.get("snippet") or "",
                                    site=r.get("site_name") or domain_of(r["url"]), date=r.get("date")))
        return out

    async def fetch(self, urls, *, image_links=False, listing_id=None, run_id=None):
        pages: list[FetchedPage] = []
        for i in range(0, len(urls), 10):
            batch = urls[i:i + 10]
            body = {"urls": batch, "format": "markdown", "image_links": image_links}
            async with track_call("tinyfish", "fetch", cost_inr=self._cost("fetch") * len(batch), listing_id=listing_id, run_id=run_id):
                async with httpx.AsyncClient(timeout=httpx.Timeout(150.0, connect=10.0)) as client:
                    resp = await client.post(self.FETCH_URL, json=body, headers=self.headers)
                if resp.status_code >= 400:
                    raise WebIntelError(f"tinyfish fetch {resp.status_code}: {resp.text[:200]}")
            data = resp.json()
            for r in data.get("results") or []:
                text = r.get("text")
                if not isinstance(text, str):
                    text = json.dumps(text)[:20000] if text else ""
                pages.append(FetchedPage(url=r.get("final_url") or r.get("url"), title=r.get("title") or "",
                                         text=text, image_links=r.get("image_links") or [],
                                         published_date=r.get("published_date")))
            for e in data.get("errors") or []:
                pages.append(FetchedPage(url=e.get("url", ""), error=str(e.get("error"))))
        return pages

    async def run_agent(self, goal, *, start_url, inputs=None, on_step=None, listing_id=None, profile_id=None):
        prompt = goal
        if inputs:
            prompt += "\n\nUse exactly these values:\n" + json.dumps(inputs, ensure_ascii=False, indent=2)
        result = AgentResult(status="FAILED", result=None)
        async with track_call("tinyfish", "agent", cost_inr=self._cost("agent"), listing_id=listing_id):
            async with httpx.AsyncClient(timeout=httpx.Timeout(600.0, connect=10.0)) as client:
                body: dict = {"url": start_url, "goal": prompt}
                if profile_id:
                    # Saved Browser Context Profile (signed-in demo seller) + Vault for stale-session repair.
                    body.update({"use_profile": True, "profile_id": profile_id, "use_vault": True})
                async with client.stream("POST", self.AGENT_SSE_URL, json=body,
                                         headers={**self.headers, "Accept": "text/event-stream"}) as resp:
                    if resp.status_code >= 400:
                        body = await resp.aread()
                        raise WebIntelError(f"tinyfish agent {resp.status_code}: {body[:200]!r}")
                    async for line in resp.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        try:
                            event = json.loads(line[5:].strip())
                        except json.JSONDecodeError:
                            continue
                        etype = event.get("type")
                        if etype == "STARTED":
                            result.run_id = event.get("run_id")
                            if on_step:
                                await on_step(AgentStep("started", "Agent started", {"run_id": result.run_id}))
                        elif etype == "STREAMING_URL":
                            result.streaming_url = event.get("streaming_url")
                            if on_step:
                                await on_step(AgentStep("streaming_url", "Live view ready", {"url": result.streaming_url}))
                        elif etype == "PROGRESS":
                            if on_step:
                                await on_step(AgentStep("progress", event.get("purpose") or "Working…"))
                        elif etype == "COMPLETE":
                            result.status = event.get("status") or "COMPLETED"
                            result.result = event.get("result") or event.get("result_json")
                            err = event.get("error")
                            result.error = err.get("message") if isinstance(err, dict) else err
                            if on_step:
                                await on_step(AgentStep("complete", "Finished", {"status": result.status}))
        return result


# --------------------------------------------------------------------------------------
# Fake: synthetic but clearly labelled market pages so the pricing pipeline runs offline.
# --------------------------------------------------------------------------------------

BASE_PRICES = {  # (handmade median, replica median) INR — rough demo anchors, not market data
    "sarees": (3000, 1100), "dupattas-stoles": (1500, 500), "kurtas-fabric": (1400, 600),
    "home-textiles": (2200, 800), "pottery-terracotta": (650, 250), "woodcraft": (1800, 700),
    "metal-brass": (2400, 900), "jewellery": (1200, 350), "bamboo-cane": (700, 300),
    "paintings": (3500, 600), "leather": (1600, 600), "toys": (600, 250), "other": (1000, 400),
}


def _stable(text: str) -> int:
    import hashlib

    return int(hashlib.sha256(text.encode()).hexdigest()[:12], 16)


class FakeWebIntel:
    name = "fake"

    async def search(self, query, *, num=10, region="IN", language="en", listing_id=None, run_id=None):
        q = query.lower()
        replica = any(w in q for w in ("printed", "replica", "machine", "power loom"))
        kind = "replica" if replica else "handmade"
        return [
            SearchResult(
                title=f"Demo {kind} listing {i + 1} for '{query}'",
                url=f"https://demo-{kind}-{i % 4}.example.com/p/{_stable(query + str(i)) % 10_000}",
                snippet="Synthetic result from the fake web provider (no TinyFish key configured).",
                site=f"demo-{kind}-{i % 4}.example.com",
            )
            for i in range(min(num, 6))
        ]

    async def fetch(self, urls, *, image_links=False, listing_id=None, run_id=None):
        from app.providers.fake_context import current_category

        hand, rep = BASE_PRICES.get(current_category(), BASE_PRICES["other"])
        pages = []
        for i, url in enumerate(urls):
            is_rep = "replica" in url
            base = rep if is_rep else hand
            factor = 0.75 + (_stable(url) % 50) / 100  # 0.75–1.24
            price = round(base * factor / 10) * 10
            words = "printed polyester, machine made" if is_rep else "handloom, handwoven by artisan weavers"
            pages.append(FetchedPage(url=url, title=f"Demo product {i + 1}",
                                     text=f"# Demo product {i + 1}\n\n{words}.\n\nPrice: ₹{price:,}\n"))
        return pages

    async def run_agent(self, goal, *, start_url, inputs=None, on_step=None, listing_id=None, profile_id=None):
        import asyncio

        steps = ["Opening the portal", "Signing in to the demo seller account", "Opening 'Add product'",
                 "Filling title", "Filling description", "Setting price and category", "Uploading photo",
                 "Submitting listing"]
        if on_step:
            await on_step(AgentStep("started", "Agent started (fake provider)", {"run_id": "fake-run"}))
        for s in steps:
            await asyncio.sleep(0.4)
            if on_step:
                await on_step(AgentStep("progress", s))
        if on_step:
            await on_step(AgentStep("complete", "Finished", {"status": "COMPLETED"}))
        return AgentResult(status="COMPLETED", result={"result_url": f"{start_url.rstrip('/')}/demo-listing", "fake": True},
                           run_id="fake-run")


_web: WebIntel | None = None


def get_webintel() -> WebIntel:
    global _web
    if _web is None:
        key = get_settings().tinyfish_api_key
        _web = TinyFishWebIntel(key) if key else FakeWebIntel()
    return _web


def set_webintel(w: WebIntel | None) -> None:
    global _web
    _web = w
