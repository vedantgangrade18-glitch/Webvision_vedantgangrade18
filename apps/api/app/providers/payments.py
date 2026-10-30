"""Payments behind `Payments` (Part 2 §10): Razorpay Standard Checkout + Route.

Karu is the marketplace merchant; each artisan is a Route linked account. Item amounts are
transferred to the artisan **on hold** and released when the return window closes.

Razorpay REST (basic auth key_id:key_secret), amounts in paise:
- POST /v1/orders · GET /v1/payments/{id} · POST /v1/payments/{id}/refund
- POST /v1/payments/{id}/transfers {transfers:[{account, amount, currency, on_hold}]}
- PATCH /v1/transfers/{id} {on_hold: 0} · POST /v1/transfers/{id}/reversals
- POST /v2/accounts → /stakeholders → /products {product_name: route} → PATCH settlements
Checkout signature: HMAC_SHA256(order_id + "|" + payment_id, key_secret).
Webhook signature: HMAC_SHA256(raw_body, webhook_secret) in `X-Razorpay-Signature`.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.core.audit import track_call
from app.core.config import get_settings


class PaymentsError(Exception):
    pass


@dataclass
class LinkedAccountResult:
    account_id: str | None
    product_id: str | None
    status: str  # active|pending_kyc|failed
    reason: str | None = None


class Payments(Protocol):
    name: str
    key_id: str

    async def create_order(self, amount_paise: int, receipt: str, notes: dict) -> dict: ...
    def verify_checkout_signature(self, order_id: str, payment_id: str, signature: str) -> bool: ...
    def verify_webhook(self, body: bytes, signature: str) -> bool: ...
    async def fetch_payment(self, payment_id: str) -> dict: ...
    async def create_transfer(self, payment_id: str, account_id: str, amount_paise: int, on_hold: bool, notes: dict) -> dict: ...
    async def release_hold(self, transfer_id: str) -> dict: ...
    async def reverse_transfer(self, transfer_id: str, amount_paise: int) -> dict: ...
    async def refund(self, payment_id: str, amount_paise: int, notes: dict) -> dict: ...
    async def create_linked_account(self, *, reference_id: str, name: str, email: str, phone: str, address: dict,
                                    method: str, details: dict) -> LinkedAccountResult: ...
    async def linked_account_status(self, account_id: str, product_id: str) -> LinkedAccountResult: ...


def _hmac(secret: str, msg: bytes) -> str:
    return hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()


class RazorpayPayments:
    name = "razorpay"
    BASE = "https://api.razorpay.com"

    def __init__(self, key_id: str, key_secret: str, webhook_secret: str):
        self.key_id = key_id
        self.key_secret = key_secret
        self.webhook_secret = webhook_secret

    async def _req(self, method: str, path: str, json: dict | None = None, op: str = "") -> dict:
        async with track_call("razorpay", op or path.split("/")[2]):
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0), auth=(self.key_id, self.key_secret)) as c:
                resp = await c.request(method, f"{self.BASE}{path}", json=json)
            if resp.status_code >= 400:
                raise PaymentsError(f"razorpay {method} {path} {resp.status_code}: {resp.text[:300]}")
        return resp.json()

    async def create_order(self, amount_paise, receipt, notes):
        return await self._req("POST", "/v1/orders", {"amount": amount_paise, "currency": "INR", "receipt": receipt[:40],
                                                      "notes": notes}, op="order.create")

    def verify_checkout_signature(self, order_id, payment_id, signature):
        expected = _hmac(self.key_secret, f"{order_id}|{payment_id}".encode())
        return hmac.compare_digest(expected, signature or "")

    def verify_webhook(self, body, signature):
        if not self.webhook_secret:
            return False
        return hmac.compare_digest(_hmac(self.webhook_secret, body), signature or "")

    async def fetch_payment(self, payment_id):
        return await self._req("GET", f"/v1/payments/{payment_id}", op="payment.fetch")

    async def create_transfer(self, payment_id, account_id, amount_paise, on_hold, notes):
        res = await self._req("POST", f"/v1/payments/{payment_id}/transfers", {
            "transfers": [{"account": account_id, "amount": amount_paise, "currency": "INR",
                           "on_hold": 1 if on_hold else 0, "notes": notes}]
        }, op="transfer.create")
        items = res.get("items") or []
        if not items:
            raise PaymentsError("razorpay returned no transfer")
        return items[0]

    async def release_hold(self, transfer_id):
        return await self._req("PATCH", f"/v1/transfers/{transfer_id}", {"on_hold": 0}, op="transfer.release")

    async def reverse_transfer(self, transfer_id, amount_paise):
        return await self._req("POST", f"/v1/transfers/{transfer_id}/reversals", {"amount": amount_paise}, op="transfer.reverse")

    async def refund(self, payment_id, amount_paise, notes):
        return await self._req("POST", f"/v1/payments/{payment_id}/refund", {"amount": amount_paise, "speed": "normal",
                                                                              "notes": notes}, op="refund.create")

    async def create_linked_account(self, *, reference_id, name, email, phone, address, method, details):
        if method != "bank":
            # Linked accounts settle to either a bank account or a VPA; this integration ships the
            # bank path. UPI artisans are onboarded by ops until the VPA path is enabled.
            return LinkedAccountResult(None, None, "failed", "upi_settlement_not_enabled")
        s = get_settings()
        acc = await self._req("POST", "/v2/accounts", {
            "email": email,
            "phone": phone[-10:],
            "type": "route",
            "reference_id": reference_id[:20],
            "legal_business_name": name[:200] if len(name) >= 4 else f"{name} Crafts",
            "business_type": "individual",
            "contact_name": name,
            "profile": {
                "category": s.razorpay_la_category,
                "subcategory": s.razorpay_la_subcategory,
                "addresses": {"registered": {
                    "street1": address.get("street1") or address.get("village_town") or "NA",
                    "street2": address.get("street2") or address.get("district") or "NA",
                    "city": address.get("city") or address.get("district") or "NA",
                    "state": (address.get("state") or "").upper(),
                    "postal_code": address.get("pin_code") or "",
                    "country": "IN",
                }},
            },
        }, op="account.create")
        account_id = acc["id"]
        await self._req("POST", f"/v2/accounts/{account_id}/stakeholders", {"name": name, "email": email}, op="stakeholder.create")
        product = await self._req("POST", f"/v2/accounts/{account_id}/products",
                                  {"product_name": "route", "tnc_accepted": True}, op="product.request")
        product_id = product["id"]
        product = await self._req("PATCH", f"/v2/accounts/{account_id}/products/{product_id}", {
            "settlements": {"account_number": details["account_number"], "ifsc_code": details["ifsc"],
                            "beneficiary_name": details.get("beneficiary_name") or name},
            "tnc_accepted": True,
        }, op="product.update")
        return LinkedAccountResult(account_id, product_id, _map_activation(product.get("activation_status")))

    async def linked_account_status(self, account_id, product_id):
        product = await self._req("GET", f"/v2/accounts/{account_id}/products/{product_id}", op="product.fetch")
        return LinkedAccountResult(account_id, product_id, _map_activation(product.get("activation_status")))


def _map_activation(status: str | None) -> str:
    return {"activated": "active", "suspended": "failed"}.get(status or "", "pending_kyc")


class FakePayments:
    """Test-mode stand-in: a Karu-hosted test checkout calls `/orders/{id}/payment/fake-complete`."""

    name = "fake"
    key_id = "rzp_test_fake"
    secret = "fake-secret"

    async def create_order(self, amount_paise, receipt, notes):
        return {"id": f"order_fake{secrets.token_hex(6)}", "amount": amount_paise, "currency": "INR", "receipt": receipt}

    def sign(self, order_id: str, payment_id: str) -> str:
        return _hmac(self.secret, f"{order_id}|{payment_id}".encode())

    def verify_checkout_signature(self, order_id, payment_id, signature):
        return hmac.compare_digest(self.sign(order_id, payment_id), signature or "")

    def verify_webhook(self, body, signature):
        return hmac.compare_digest(_hmac(self.secret, body), signature or "")

    async def fetch_payment(self, payment_id):
        return {"id": payment_id, "status": "captured", "method": "upi"}

    async def create_transfer(self, payment_id, account_id, amount_paise, on_hold, notes):
        return {"id": f"trf_fake{secrets.token_hex(6)}", "on_hold": on_hold, "amount": amount_paise}

    async def release_hold(self, transfer_id):
        return {"id": transfer_id, "on_hold": False, "settlement_status": "pending"}

    async def reverse_transfer(self, transfer_id, amount_paise):
        return {"id": f"rvrsl_fake{secrets.token_hex(6)}", "transfer_id": transfer_id, "amount": amount_paise}

    async def refund(self, payment_id, amount_paise, notes):
        return {"id": f"rfnd_fake{secrets.token_hex(6)}", "status": "processed", "amount": amount_paise}

    async def create_linked_account(self, *, reference_id, name, email, phone, address, method, details):
        return LinkedAccountResult(f"acc_fake{secrets.token_hex(5)}", f"acc_prd_fake{secrets.token_hex(4)}", "active")

    async def linked_account_status(self, account_id, product_id):
        return LinkedAccountResult(account_id, product_id, "active")


_payments: Payments | None = None


def get_payments() -> Payments:
    global _payments
    if _payments is None:
        s = get_settings()
        _payments = (
            RazorpayPayments(s.razorpay_key_id, s.razorpay_key_secret, s.razorpay_webhook_secret)
            if s.razorpay_key_id and s.razorpay_key_secret
            else FakePayments()
        )
    return _payments


def set_payments(p: Payments | None) -> None:
    global _payments
    _payments = p
