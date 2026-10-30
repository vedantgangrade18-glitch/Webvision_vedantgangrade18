"""SMS, WhatsApp and email behind `Messaging` (Part 2 §9.7).

- SMS: MSG91 Flow API (template variables) when SMS_PROVIDER_KEY is set.
- WhatsApp: Meta WhatsApp Cloud API template messages (`/{phone_id}/messages`), language
  per template; template names are `karu_{type}` and must be approved per language.
- Email: Resend (`POST https://api.resend.com/emails`).
- Fake: logs and keeps an in-memory outbox (tests, local demo shows OTPs in the UI).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Protocol

import httpx

from app.core.audit import track_call
from app.core.config import get_settings

log = logging.getLogger("karu.messaging")

WA_LANG = {"hi": "hi", "en": "en", "pa": "pa", "mr": "mr", "gu": "gu", "ur": "ur", "ta": "ta", "ml": "ml"}


class MessagingError(Exception):
    pass


@dataclass
class SentMessage:
    channel: str
    to: str
    body: str
    template: str | None = None
    params: list[str] = field(default_factory=list)


class Messaging(Protocol):
    name: str

    async def send_sms(self, to_e164: str, text: str, *, template_vars: dict | None = None) -> str: ...
    async def send_whatsapp(self, to_e164: str, template: str, locale: str, params: list[str], fallback_text: str) -> str: ...
    async def send_email(self, to: str, subject: str, text: str) -> str: ...


class LiveMessaging:
    name = "live"

    def __init__(self):
        self.s = get_settings()

    async def send_sms(self, to_e164, text, *, template_vars=None):
        if not self.s.sms_provider_key or not self.s.msg91_template_id:
            raise MessagingError("sms provider not configured")
        body = {"template_id": self.s.msg91_template_id, "short_url": "0",
                "recipients": [{"mobiles": to_e164.lstrip("+"), **(template_vars or {"message": text})}]}
        async with track_call("sms", "msg91.flow"):
            async with httpx.AsyncClient(timeout=15) as c:
                resp = await c.post("https://control.msg91.com/api/v5/flow", json=body,
                                    headers={"authkey": self.s.sms_provider_key, "accept": "application/json"})
            if resp.status_code >= 400:
                raise MessagingError(f"msg91 {resp.status_code}: {resp.text[:200]}")
        return resp.json().get("request_id", "")

    async def send_whatsapp(self, to_e164, template, locale, params, fallback_text):
        if not self.s.whatsapp_token or not self.s.whatsapp_phone_id:
            raise MessagingError("whatsapp not configured")
        body = {
            "messaging_product": "whatsapp",
            "to": to_e164.lstrip("+"),
            "type": "template",
            "template": {
                "name": template,
                "language": {"code": WA_LANG.get(locale, "en")},
                "components": [{"type": "body", "parameters": [{"type": "text", "text": p[:1000]} for p in params]}],
            },
        }
        async with track_call("whatsapp", "cloud.template"):
            async with httpx.AsyncClient(timeout=15) as c:
                resp = await c.post(f"https://graph.facebook.com/v21.0/{self.s.whatsapp_phone_id}/messages", json=body,
                                    headers={"Authorization": f"Bearer {self.s.whatsapp_token}"})
            if resp.status_code >= 400:
                raise MessagingError(f"whatsapp {resp.status_code}: {resp.text[:200]}")
        msgs = resp.json().get("messages") or [{}]
        return msgs[0].get("id", "")

    async def send_email(self, to, subject, text):
        if not self.s.email_api_key:
            raise MessagingError("email not configured")
        async with track_call("email", "resend.send"):
            async with httpx.AsyncClient(timeout=15) as c:
                resp = await c.post("https://api.resend.com/emails",
                                    json={"from": self.s.email_from, "to": [to], "subject": subject, "text": text},
                                    headers={"Authorization": f"Bearer {self.s.email_api_key}"})
            if resp.status_code >= 400:
                raise MessagingError(f"resend {resp.status_code}: {resp.text[:200]}")
        return resp.json().get("id", "")


class FakeMessaging:
    name = "fake"

    def __init__(self):
        self.outbox: list[SentMessage] = []

    async def send_sms(self, to_e164, text, *, template_vars=None):
        self.outbox.append(SentMessage("sms", to_e164, text))
        log.info("[fake sms] to=%s… %s", to_e164[:6], text)
        return f"fake-sms-{len(self.outbox)}"

    async def send_whatsapp(self, to_e164, template, locale, params, fallback_text):
        self.outbox.append(SentMessage("whatsapp", to_e164, fallback_text, template, params))
        log.info("[fake whatsapp] to=%s… %s", to_e164[:6], fallback_text)
        return f"fake-wa-{len(self.outbox)}"

    async def send_email(self, to, subject, text):
        self.outbox.append(SentMessage("email", to, f"{subject}\n\n{text}"))
        log.info("[fake email] to=%s subject=%s", to.split("@")[0][:2] + "…", subject)
        return f"fake-email-{len(self.outbox)}"


_messaging: Messaging | None = None


def messaging_is_fake() -> bool:
    return isinstance(get_messaging(), FakeMessaging)


def get_messaging() -> Messaging:
    global _messaging
    if _messaging is None:
        s = get_settings()
        live = s.sms_provider_key or s.whatsapp_token or s.email_api_key
        _messaging = LiveMessaging() if live else FakeMessaging()
    return _messaging


def set_messaging(m: Messaging | None) -> None:
    global _messaging
    _messaging = m
