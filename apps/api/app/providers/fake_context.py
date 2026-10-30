"""Context for fake providers (lets the fake web provider shape prices by category)."""

from contextvars import ContextVar

_category: ContextVar[str] = ContextVar("fake_category", default="other")


def set_category(slug: str | None) -> None:
    _category.set(slug or "other")


def current_category() -> str:
    return _category.get()
