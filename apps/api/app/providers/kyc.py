"""Aadhaar KYC via DigiLocker through a licensed provider (Part 2 §11.2).

Karu stores only: status, last 4 digits, name-match result, provider reference, timestamp.
Never the full number, XML or PDF.

The provider contract below matches how DigiLocker-based KYC providers (Digio, Setu,
HyperVerge, Signzy …) work: start → redirect the artisan to DigiLocker consent → callback
with a reference → fetch the verified identity summary. Each vendor's request shapes differ,
so the live adapter is written once the team signs a vendor. Until then the fake provider
runs the same flow with a Karu-hosted consent page (clearly marked as a test).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.core.config import get_settings
from app.core.security import sign_payload, verify_payload


@dataclass
class KycResult:
    status: str  # verified|failed|pending
    name: str | None
    dob: str | None
    last4: str | None
    reference: str | None
    reason: str | None = None


class KYC(Protocol):
    name: str

    async def start(self, artisan_id: str, redirect_url: str) -> str: ...
    async def complete(self, params: dict) -> KycResult: ...


class FakeKYC:
    name = "fake"

    async def start(self, artisan_id, redirect_url):
        state = sign_payload({"a": artisan_id, "r": redirect_url}, minutes=30)
        return f"{get_settings().api_base_url}/api/v1/artisan/kyc/aadhaar/fake?state={state}"

    async def complete(self, params):
        try:
            verify_payload(params.get("state", ""))
        except Exception:  # noqa: BLE001
            return KycResult("failed", None, None, None, None, "invalid_state")
        if params.get("decision") != "approve":
            return KycResult("failed", None, None, None, None, "user_declined")
        return KycResult("verified", params.get("name") or None, None, params.get("last4") or "0000",
                         f"fake-kyc-{params.get('state', '')[-8:]}")


_kyc: KYC | None = None


def get_kyc() -> KYC:
    global _kyc
    if _kyc is None:
        _kyc = FakeKYC()
    return _kyc
