"""The one place listing attribute shape and meaning are decided.

The LLM only fills values. What applies to a category, what counts as missing and what a
buyer sees come from the field specs in `Category.attribute_schema` (seeded from
`reference.py`), deterministically, at extraction time and on every PATCH.
"""

from __future__ import annotations

from typing import Any

from app.modules.catalog.reference import CATEGORIES


def fields_of(schema: dict | None) -> list[dict]:
    return list((schema or {}).get("fields") or [])


# Every known field across categories, in first-seen order. Values for any of these survive a
# category switch (hidden from buyers, still editable by the artisan); anything else is dropped.
ALL_FIELDS: dict[str, dict] = {}
for _, _, _, _schema in CATEGORIES:
    for _spec in fields_of(_schema):
        ALL_FIELDS.setdefault(_spec["key"], _spec)
# Legacy flat keys ("length_m") → dotted path ("dimensions.length_m").
_LEAF = {k.rsplit(".", 1)[-1]: k for k in ALL_FIELDS if "." in k}


def _flatten(attrs: dict, prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in (attrs or {}).items():
        path = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(_flatten(v, f"{path}."))
        else:
            out[_LEAF.get(path, path)] = v
    return out


def _coerce(type_: str, v: Any) -> Any:
    if v is None:
        return None
    if type_ in ("number", "integer"):
        try:
            n = float(str(v).replace(",", "").strip())
        except ValueError:
            return None
        if n <= 0:
            return None
        return int(round(n)) if type_ == "integer" else n
    if type_ == "array":
        items = v.split(",") if isinstance(v, str) else v if isinstance(v, list) else [v]
        items = [str(x).strip()[:60] for x in items if str(x).strip()]
        return items[:10] or None
    s = str(v).strip()[:200]
    return s or None


def get(attrs: dict | None, path: str) -> Any:
    cur: Any = attrs or {}
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def normalize(attrs: dict | None) -> dict:
    """Any input shape (nested, dotted or legacy flat keys) → nested dict of known, typed, non-empty values."""
    out: dict = {}
    for path, raw in _flatten(attrs or {}).items():
        spec = ALL_FIELDS.get(path)
        value = _coerce(spec["type"], raw) if spec else None
        if value is None:
            continue
        *parents, leaf = path.split(".")
        node = out
        for p in parents:
            node = node.setdefault(p, {})
        node[leaf] = value
    return out


def for_category(schema: dict | None, attrs: dict | None) -> dict:
    """Only the fields that belong to the listing's category (what buyers and marketplaces see)."""
    keep = {s["key"] for s in fields_of(schema)}
    return normalize({k: v for k, v in _flatten(attrs or {}).items() if k in keep})


def missing_fields(schema: dict | None, attrs: dict | None, *, price: Any, has_category: bool) -> list[str]:
    missing = [s["key"] for s in fields_of(schema) if s["tier"] == "core" and get(attrs, s["key"]) is None]
    if price is None:
        missing.append("price_inr")
    if not has_category:
        missing.append("category_slug")
    return missing


def notes_for_artisan(*, price: Any, keep: list[str] | None = None) -> list[str]:
    notes = [n for n in (keep or []) if n == "manual_form"]
    if price is None:
        notes.append("price")
    return notes


_JSON_TYPES = {"string": {"type": "string"}, "number": {"type": "number"}, "integer": {"type": "integer"},
               "array": {"type": "array", "items": {"type": "string"}}}


def llm_schema() -> tuple[dict, list[str]]:
    """JSON schema for `attributes` (union of all category fields) + top-level keys for field_confidence."""
    props: dict = {}
    for path, spec in ALL_FIELDS.items():
        *parents, leaf = path.split(".")
        node = props
        for p in parents:
            node = node.setdefault(p, {"type": "object", "properties": {}})["properties"]
        node[leaf] = _JSON_TYPES[spec["type"]]
    return {"type": "object", "properties": props}, list(props)
