"""Deterministic answers for the fake LLM, one function per purpose.

These keep every flow usable without a Gemini key. They are rule-based (keyword tables,
regexes, templates); they are not models and the UI/staff views label them as fake.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from app.providers.llm import rule_based_extract

CATEGORY_NOUN = {
    "sarees": ("saree", "साड़ी"),
    "dupattas-stoles": ("dupatta", "दुपट्टा"),
    "kurtas-fabric": ("fabric", "कपड़ा"),
    "home-textiles": ("home textile", "घरेलू वस्त्र"),
    "pottery-terracotta": ("pot", "मिट्टी का बर्तन"),
    "woodcraft": ("woodcraft piece", "लकड़ी की कलाकृति"),
    "metal-brass": ("brass piece", "पीतल की कलाकृति"),
    "jewellery": ("jewellery", "आभूषण"),
    "bamboo-cane": ("bamboo piece", "बांस की कलाकृति"),
    "paintings": ("painting", "चित्र"),
    "leather": ("leather piece", "चमड़े का सामान"),
    "toys": ("toy", "खिलौना"),
    "other": ("handmade piece", "हस्तनिर्मित वस्तु"),
}
MATERIAL_HI = {"cotton": "सूती", "silk": "रेशमी", "wool": "ऊनी", "terracotta": "मिट्टी", "brass": "पीतल",
               "wood": "लकड़ी", "bamboo": "बांस", "linen": "लिनन"}
TECHNIQUE_HI = {"handloom": "हथकरघा", "hand block print": "हाथ की ब्लॉक छपाई", "hand embroidery": "हाथ की कढ़ाई",
                "wheel thrown": "चाक पर बना", "hand painted": "हाथ से चित्रित", "lost wax casting": "ढोकरा ढलाई",
                "hand carved": "हाथ की नक्काशी"}
DYE_HI = {"natural indigo": "प्राकृतिक नील", "natural dye": "प्राकृतिक रंग", "chemical dye": "रासायनिक रंग"}


def _jitter(seed: str, spread: float) -> float:
    h = int(hashlib.sha256(seed.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return (h - 0.5) * 2 * spread


def _describe(ctx: dict, variant: int = 0) -> dict:
    attrs: dict = ctx.get("attributes") or {}
    cat = ctx.get("category_slug") or "other"
    noun_en, noun_hi = CATEGORY_NOUN.get(cat, CATEGORY_NOUN["other"])
    material = attrs.get("material")
    technique = attrs.get("technique")
    dye = attrs.get("dye")
    craft = ctx.get("craft_name") or ""
    place = ctx.get("place") or ""
    days = attrs.get("time_to_make_days")
    colours = attrs.get("colour") or []

    en_bits = [b for b in [craft or None, technique.title() if technique and not craft else None,
                           material.title() if material else None, noun_en.title()] if b]
    title_en = " ".join(dict.fromkeys(en_bits)) or "Handmade Piece"
    if dye and "indigo" in dye:
        title_en = f"Indigo {title_en}" if variant % 2 == 0 else f"{title_en} in Natural Indigo"
    hi_bits = [b for b in [TECHNIQUE_HI.get(technique) if technique else None, MATERIAL_HI.get(material) if material else None, noun_hi] if b]
    title_hi = " ".join(hi_bits)
    if dye and "indigo" in dye:
        title_hi = f"नील रंग की {title_hi}"

    sentences_en = []
    first = f"A {technique} {noun_en}" if technique else f"A handmade {noun_en}"
    if material:
        first += f" in {material}"
    if place:
        first += f", made in {place}"
    sentences_en.append(first + ".")
    if dye:
        sentences_en.append(f"Coloured with {dye}.")
    if colours:
        sentences_en.append(f"Colours: {', '.join(colours)}.")
    dims = attrs.get("dimensions") or {}
    if dims.get("length_m"):
        sentences_en.append(f"Length: {dims['length_m']} m.")
    if days:
        sentences_en.append(f"It took {days} days to make by hand.")
    sentences_en.append("Each piece is slightly different, a mark of the maker's hand.")
    if attrs.get("care"):
        sentences_en.append(f"Care: {attrs['care']}.")

    sentences_hi = []
    s1 = f"यह {TECHNIQUE_HI.get(technique, 'हस्तनिर्मित')} {noun_hi}"
    if material:
        s1 += f", {MATERIAL_HI.get(material, material)}"
    if place:
        s1 += f", {place} में बनी"
    sentences_hi.append(s1 + " है।")
    if dye:
        sentences_hi.append(f"इसे {DYE_HI.get(dye, dye)} से रंगा गया है।")
    if dims.get("length_m"):
        sentences_hi.append(f"लंबाई {dims['length_m']} मीटर है।")
    if days:
        sentences_hi.append(f"इसे हाथ से बनाने में {days} दिन लगे।")
    sentences_hi.append("हर टुकड़ा थोड़ा अलग होता है, यह कारीगर के हाथ की पहचान है।")

    src = ctx.get("source_lang") or "hi"
    title = {"en": title_en, "hi": title_hi}
    description = {"en": " ".join(sentences_en), "hi": " ".join(sentences_hi)}
    transcript = (ctx.get("transcript") or "").strip()
    if src not in title:
        title[src] = title_en
        # The artisan's own words are the most faithful source-language description.
        description[src] = transcript or description["en"]
    tags = [t for t in [cat, material, technique, dye, *(colours or []), craft.lower() if craft else None] if t]
    return {"title": title, "description": description, "tags": list(dict.fromkeys(tags))[:10]}


_PRICE_RE = re.compile(r"(?:₹|rs\.?|inr)\s?([0-9][0-9,]{1,8}(?:\.\d{1,2})?)", re.I)
HANDMADE_WORDS = ("handloom", "handwoven", "hand woven", "handmade", "hand-made", "hand block", "artisan",
                  "hand embroidered", "hand painted", "gi tag", "gi-tagged", "weaver", "हथकरघा", "हस्तनिर्मित")
REPLICA_WORDS = ("printed", "power loom", "powerloom", "machine", "synthetic", "polyester", "digital print",
                 "replica", "copy", "imitation", "faux")


def regex_price_extract(page: dict) -> dict:
    text = (page.get("text") or "")[:20000]
    low = text.lower()
    prices = []
    for m in _PRICE_RE.finditer(text):
        try:
            v = float(m.group(1).replace(",", ""))
        except ValueError:
            continue
        if 50 <= v <= 500000:
            prices.append(v)
    hand = sum(low.count(w) for w in HANDMADE_WORDS)
    repl = sum(low.count(w) for w in REPLICA_WORDS)
    klass = "handmade" if hand > repl and hand >= 1 else ("replica" if repl > hand else "unknown")
    items = []
    if prices:
        # The product price is usually the first or most frequent price on a product page.
        price = max(set(prices[:6]), key=prices[:6].count)
        items.append({
            "title": page.get("title") or "",
            "price_inr": price,
            "currency": "INR",
            "handmade_claims": [w for w in HANDMADE_WORDS if w in low][:4],
            "seller_type": "unknown",
            "klass": klass,
            "confidence": 0.45,
        })
    return {"items": items}


def answer(purpose: str, ctx: dict, *, images=None, video=None, temperature: float = 0.2) -> dict[str, Any]:
    if purpose == "extract":
        return rule_based_extract(ctx.get("transcript", ""), ctx.get("category_slugs", []))
    if purpose == "describe":
        return _describe(ctx, variant=int(ctx.get("variant", 0)))
    if purpose == "regenerate_field":
        field = ctx.get("field")
        variant = int(ctx.get("variant", 1))
        d = _describe(ctx, variant=variant)
        if field == "title":
            return {"title": d["title"]}
        if field == "description":
            def rotate(text: str) -> str:
                parts = [p for p in re.split(r"(?<=[.।])\s+", text) if p]
                if len(parts) < 2:
                    return text
                k = variant % len(parts)
                return " ".join(parts[k:] + parts[:k])

            return {"description": {k: rotate(v) for k, v in d["description"].items()}}
        if field == "tags":
            return {"tags": d["tags"]}
        if field == "attributes":
            return {"attributes": rule_based_extract(ctx.get("transcript", ""), ctx.get("category_slugs", []))["attributes"]}
        return {}
    if purpose == "l1_rubric":
        if "force_handmade_probability" in ctx:
            h = float(ctx["force_handmade_probability"])
        else:
            seed = ctx.get("seed", "") or (hashlib.sha256(images[0][0]).hexdigest() if images else "none")
            h = 0.82 + _jitter(seed, 0.06)
        return {
            "handmade_probability": round(max(0.0, min(1.0, h)), 3),
            "cues_for": ["fake provider: no visual analysis performed"],
            "cues_against": [],
            "provider": "fake",
        }
    if purpose == "l3_video":
        if "force_process_score" in ctx:
            p = float(ctx["force_process_score"])
        else:
            p = 80 + _jitter(ctx.get("seed", "v"), 6)
        return {
            "process_score": round(p, 1),
            "shows_hands_at_work": True,
            "shows_tools": True,
            "technique_matches_claim": True,
            "same_item_as_photos": bool(ctx.get("force_same_item", True)),
            "same_item_confidence": 0.85,
            "minor_visible": False,
            "evidence": [{"t_s": 0, "cue": "fake provider: no video analysis performed"}],
            "provider": "fake",
        }
    if purpose == "price_extract":
        return regex_price_extract(ctx.get("page", {}))
    if purpose == "translate":
        return {"text": ctx.get("text", ""), "untranslated": True}
    if purpose == "transcribe":
        return {"text": ctx.get("fallback_text", ""), "language": ctx.get("lang", "hi")}
    if purpose == "name_match":
        a, b = (ctx.get("a") or "").lower(), (ctx.get("b") or "").lower()
        return {"match": bool(a and b and (a in b or b in a)), "confidence": 0.6}
    return {}
