"""LLM / vision provider (Google Gemini) behind one interface (Part 2 §2, §6.2).

Real: Gemini `generateContent` REST API with structured JSON output (`responseMimeType`
+ `responseJsonSchema`), images/audio/video passed inline (videos are analysed on a low-res
proxy, keep < 18 MB). Model names come from config, not code.

Fake: deterministic, rule-based answers built from `fake_context`, so every flow works
offline (demo rehearsals, tests). It never pretends to be a classifier: outputs are
marked `"provider": "fake"` and staff views show it.
"""

from __future__ import annotations

import base64
import json
import os
import re
from typing import Any, Protocol

import httpx

from app.core.audit import track_call
from app.core.config import get_settings

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
MAX_INLINE_BYTES = 18 * 1024 * 1024


class LLMError(Exception):
    pass


class LLM(Protocol):
    name: str

    async def generate_json(
        self,
        prompt: str,
        *,
        schema: dict,
        purpose: str,
        images: list[tuple[bytes, str]] | None = None,
        video: tuple[bytes, str] | None = None,
        audio: tuple[bytes, str] | None = None,
        temperature: float = 0.2,
        model: str | None = None,
        fake_context: dict | None = None,
        listing_id=None,
        run_id=None,
    ) -> dict: ...


def _to_gemini_schema(schema: Any) -> Any:
    """Keep the JSON Schema to the subset Gemini's `responseJsonSchema` handles well."""
    if isinstance(schema, dict):
        out = {}
        for k, v in schema.items():
            if k in ("additionalProperties", "$schema", "title", "default"):
                continue
            if k == "properties" and isinstance(v, dict):
                out["properties"] = {prop_name: _to_gemini_schema(prop_val) for prop_name, prop_val in v.items()}
            else:
                out[k] = _to_gemini_schema(v)
        return out
    if isinstance(schema, list):
        return [_to_gemini_schema(v) for v in schema]
    return schema


class GeminiLLM:
    name = "gemini"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def generate_json(self, prompt, *, schema, purpose, images=None, video=None, audio=None,
                            temperature=0.2, model=None, fake_context=None, listing_id=None, run_id=None):
        s = get_settings()
        model = model or (s.gemini_model_vision if (images or video) else s.gemini_model_extract)
        parts: list[dict] = [{"text": prompt}]
        total = 0
        for data, mime in images or []:
            total += len(data)
            parts.append({"inline_data": {"mime_type": mime, "data": base64.b64encode(data).decode()}})
        for media in (video, audio):
            if media:
                data, mime = media
                total += len(data)
                parts.append({"inline_data": {"mime_type": mime, "data": base64.b64encode(data).decode()}})
        if total > MAX_INLINE_BYTES:
            raise LLMError("inline payload too large; send a smaller proxy")
        body = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json",
                "responseJsonSchema": _to_gemini_schema(schema),
            },
        }
        from app.core.appconfig import DEFAULTS

        cost = DEFAULTS["costs.v1"]["gemini.video" if video else "gemini.call"]
        async with track_call("gemini", purpose, cost_inr=cost, listing_id=listing_id, run_id=run_id):
            async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
                resp = await client.post(
                    GEMINI_URL.format(model=model), json=body, headers={"x-goog-api-key": self.api_key}
                )
            if resp.status_code >= 400:
                raise LLMError(f"gemini {resp.status_code}: {resp.text[:300]}")
            data = resp.json()
        try:
            text = "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
            result = json.loads(text)
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            raise LLMError(f"unparseable gemini response: {exc}") from exc
        if isinstance(result, dict):
            result.setdefault("_model", model)
        return result


# --------------------------------------------------------------------------------------
# Fake
# --------------------------------------------------------------------------------------

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "sarees": ["saree", "sari", "साड़ी", "साडी", "ਸਾੜੀ", "સાડી", "புடவை", "சேலை", "സാരി", "ساڑی"],
    "dupattas-stoles": ["dupatta", "stole", "दुपट्टा", "ओढ़नी", "shawl", "शॉल", "ਦੁਪੱਟਾ", "ફૂલકારી", "phulkari", "फुलकारी"],
    "kurtas-fabric": ["kurta", "कुर्ता", "fabric", "कपड़ा", "thaan", "थान"],
    "home-textiles": ["bedsheet", "चादर", "cushion", "durrie", "दरी", "rug", "kantha", "कांथा", "quilt", "रजाई"],
    "pottery-terracotta": ["pot", "मटका", "मिट्टी", "terracotta", "pottery", "clay", "कुल्हड़", "diya", "दीया"],
    "woodcraft": ["wood", "लकड़ी", "wooden", "carved", "नक्काशी"],
    "metal-brass": ["brass", "पीतल", "dokra", "ढोकरा", "copper", "तांबा", "bell metal", "कांसा"],
    "jewellery": ["jewellery", "necklace", "हार", "earring", "झुमका", "bangle", "चूड़ी", "kangan"],
    "bamboo-cane": ["bamboo", "बांस", "cane", "बेंत", "basket", "टोकरी"],
    "paintings": ["painting", "madhubani", "मधुबनी", "warli", "वारली", "pattachitra", "पटचित्र", "चित्र", "gond", "गोंड"],
    "leather": ["leather", "चमड़ा", "jutti", "जूती", "kolhapuri", "कोल्हापुरी"],
    "toys": ["toy", "खिलौना", "channapatna", "चन्नपटना", "doll", "गुड़िया"],
}
MATERIAL_KEYWORDS: dict[str, list[str]] = {
    "cotton": ["cotton", "कॉटन", "सूती", "कपास", "ਸੂਤੀ", "સુતરાઉ", "பருத்தி", "പരുത്തി"],
    "silk": ["silk", "रेशम", "रेशमी", "सिल्क", "tussar", "tussah", "टसर", "ਰੇਸ਼ਮ", "રેશમ", "பட்டு", "പട്ട്"],
    "wool": ["wool", "ऊन", "ऊनी", "pashmina", "पश्मीना"],
    "terracotta": ["terracotta", "मिट्टी", "clay"],
    "brass": ["brass", "पीतल"],
    "wood": ["wood", "लकड़ी", "sheesham", "शीशम", "teak", "सागौन"],
    "bamboo": ["bamboo", "बांस"],
    "linen": ["linen", "लिनन"],
}
DYE_KEYWORDS: dict[str, list[str]] = {
    "natural indigo": ["indigo", "नील", "नीला", "ਨੀਲ", "ગળી", "அவுரி"],
    "natural dye": ["natural dye", "प्राकृतिक रंग", "प्राकृतिक", "vegetable dye", "हर्बल"],
    "chemical dye": ["chemical", "केमिकल", "azo"],
}
TECHNIQUE_KEYWORDS: dict[str, list[str]] = {
    "handloom": ["handloom", "हथकरघा", "करघा", "loom", "बुना", "बुनाई", "woven", "ਖੱਡੀ", "હાથશાળ", "கைத்தறி", "കൈത്തറി"],
    "hand block print": ["block print", "ब्लॉक", "छपाई", "ajrakh", "अजरख", "bagru", "बगरू"],
    "hand embroidery": ["embroidery", "कढ़ाई", "कसीदा", "chikankari", "चिकनकारी", "ਕਢਾਈ", "ભરતકામ"],
    "wheel thrown": ["wheel", "चाक", "thrown"],
    "hand painted": ["hand painted", "हाथ से पेंट", "हाथ से बना चित्र", "painted", "पेंटिंग"],
    "lost wax casting": ["lost wax", "dokra", "ढोकरा"],
    "hand carved": ["carved", "नक्काशी", "carving"],
}
COLOUR_KEYWORDS: dict[str, list[str]] = {
    "indigo": ["indigo", "नील"], "blue": ["blue", "नीला", "नीली"], "red": ["red", "लाल"], "white": ["white", "सफ़ेद", "सफेद"],
    "black": ["black", "काला", "काली"], "yellow": ["yellow", "पीला", "पीली"], "green": ["green", "हरा", "हरी"],
    "maroon": ["maroon", "मैरून"], "gold": ["gold", "सुनहरा", "zari", "ज़री", "जरी"], "pink": ["pink", "गुलाबी"],
    "orange": ["orange", "नारंगी", "केसरिया"], "brown": ["brown", "भूरा", "भूरी"],
}

_HI_NUMBERS = {
    "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पाँच": 5, "पांच": 5, "छह": 6, "छः": 6, "सात": 7, "आठ": 8, "नौ": 9,
    "दस": 10, "पंद्रह": 15, "बीस": 20, "पच्चीस": 25, "तीस": 30, "चालीस": 40, "पचास": 50,
}


def _find(text: str, table: dict[str, list[str]]) -> list[str]:
    low = text.lower()
    return [k for k, words in table.items() if any(w.lower() in low for w in words)]


def rule_based_extract(transcript: str, category_slugs: list[str]) -> dict:
    """Offline extraction used by the fake LLM (and as a safety net)."""
    text = transcript or ""
    low = text.lower()
    cats = [c for c in _find(text, CATEGORY_KEYWORDS) if c in category_slugs] or []
    category = cats[0] if cats else None
    materials = _find(text, MATERIAL_KEYWORDS)
    dyes = _find(text, DYE_KEYWORDS)
    techniques = _find(text, TECHNIQUE_KEYWORDS)
    colours = _find(text, COLOUR_KEYWORDS)

    price = None
    price_conf = 0.0
    m = re.search(
        r"(?:₹|rs\.?|inr|rupees?|रुपये|रुपए|रूपए|कीमत|दाम|price|दाम)\s*[:\-]?\s*(\d[\d,]*)|(\d[\d,]*)\s*(?:₹|rs\.?|rupees?|रुपये|रुपए|रूपए|रुपया|/-)",
        low,
    )
    if m:
        price = int((m.group(1) or m.group(2)).replace(",", ""))
        price_conf = 0.9
    days = None
    dm = re.search(r"(\d+)\s*(?:days?|दिन|ਦਿਨ|દિવસ|நாள்|ദിവസ)", low)
    if dm:
        days = int(dm.group(1))
    else:
        for word, num in _HI_NUMBERS.items():
            if re.search(rf"{word}\s*दिन", text):
                days = num
                break
    length = None
    lm = re.search(r"(\d+(?:\.\d+)?)\s*(?:m\b|metre|meter|मीटर)", low)
    if lm:
        length = float(lm.group(1))
    elif "साढ़े पाँच मीटर" in text or "साढ़े पांच मीटर" in text:
        length = 5.5
    qty = None
    qm = re.search(r"(\d+)\s*(?:pieces?|pcs|नग|पीस|piece)", low)
    if qm:
        qty = int(qm.group(1))

    attributes: dict[str, Any] = {}
    if materials:
        attributes["material"] = materials[0]
    if techniques:
        attributes["technique"] = techniques[0]
    if dyes:
        attributes["dye"] = dyes[0]
    if days:
        attributes["time_to_make_days"] = days
    if length:
        attributes["dimensions"] = {"length_m": length}
    if colours:
        attributes["colour"] = colours[:3]

    missing = [f for f in ("material", "technique", "dimensions") if f not in attributes]
    if price is None:
        missing.append("price_inr")
    confidence = {"price_inr": price_conf, "category_slug": 0.8 if category else 0.3}
    for key in ("material", "technique", "dye", "time_to_make_days", "dimensions", "colour"):
        if key in attributes:
            confidence[key] = 0.75
    notes = []
    if price is None:
        notes.append("price")
    if "dimensions" in missing:
        notes.append("dimensions")
    return {
        "category_slug": category,
        "craft_slug": None,
        "attributes": attributes,
        "price_inr": price,
        "quantity_mentioned": qty,
        "field_confidence": confidence,
        "missing_fields": missing,
        "notes_for_artisan": notes,
    }


class FakeLLM:
    name = "fake"

    async def generate_json(self, prompt, *, schema, purpose, images=None, video=None, audio=None,
                            temperature=0.2, model=None, fake_context=None, listing_id=None, run_id=None):
        ctx = fake_context or {}
        from app.providers import fake_llm_answers

        result = fake_llm_answers.answer(purpose, ctx, images=images, video=video, temperature=temperature)
        result.setdefault("_model", "fake")
        return result


_llm: LLM | None = None


class VertexLLM:
    name = "vertex"

    def __init__(self, project: str, location: str = "us-central1", credentials=None):
        from google import genai

        self.project = project
        self.location = location
        self.client = genai.Client(vertexai=True, project=project, location=location, credentials=credentials)

    async def generate_json(self, prompt: str, *, schema: dict, purpose: str,
                            images: list[tuple[bytes, str]] | None = None,
                            video: tuple[bytes, str] | None = None,
                            audio: tuple[bytes, str] | None = None,
                            temperature: float = 0.2, model: str | None = None,
                            fake_context: dict | None = None, listing_id=None, run_id=None) -> dict:
        from google.genai import types

        s = get_settings()
        model = model or (s.gemini_model_vision if (images or video) else s.gemini_model_extract)

        contents: list[Any] = [prompt]
        total = 0
        for data, mime in images or []:
            total += len(data)
            contents.append(types.Part.from_bytes(data=data, mime_type=mime.split(";")[0]))
        for media in (video, audio):
            if media:
                data, mime = media
                total += len(data)
                contents.append(types.Part.from_bytes(data=data, mime_type=mime.split(";")[0]))

        if total > MAX_INLINE_BYTES:
            raise LLMError("inline payload too large; send a smaller proxy")

        config = types.GenerateContentConfig(
            temperature=temperature,
            response_mime_type="application/json",
            response_schema=_to_gemini_schema(schema),
        )

        from app.core.appconfig import DEFAULTS

        cost = DEFAULTS["costs.v1"]["gemini.video" if video else "gemini.call"]
        async with track_call("gemini", purpose, cost_inr=cost, listing_id=listing_id, run_id=run_id):
            try:
                resp = await self.client.aio.models.generate_content(
                    model=model,
                    contents=contents,
                    config=config,
                )
            except Exception as exc:
                raise LLMError(f"vertex gemini error: {exc}") from exc

        try:
            text = resp.text or ""
            result = json.loads(text)
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            raise LLMError(f"unparseable vertex gemini response: {resp.text}") from exc
        if isinstance(result, dict):
            result.setdefault("_model", model)
        return result


def get_llm() -> LLM:
    global _llm
    if _llm is None:
        s = get_settings()
        if s.env == "test":
            return FakeLLM()
        project = s.vertex_project or os.environ.get("VERTEX_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT")
        if project:
            _llm = VertexLLM(project=project, location=s.vertex_location)
        elif s.gemini_api_key:
            _llm = GeminiLLM(s.gemini_api_key)
        else:
            _llm = FakeLLM()
    return _llm


def set_llm(llm: LLM | None) -> None:
    global _llm
    _llm = llm
