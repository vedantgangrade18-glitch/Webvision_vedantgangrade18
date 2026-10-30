"""Speech-to-text behind `SpeechToText` (Part 2 §6.1).

- WhisperSTT: OpenAI `/v1/audio/transcriptions` (whisper-1), language hint = UI locale.
  Whisper covers all 8 launch languages; dialects are weaker, hence the interface.
- GeminiSTT: audio sent inline to Gemini with a verbatim-transcription prompt.
- FakeSTT: returns the transcript the browser produced with the Web Speech API (sent as
  `client_transcript`), or an empty transcript. It never invents speech.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from typing import Protocol

import httpx

from app.core.audit import track_call
from app.core.config import get_settings


@dataclass
class Transcript:
    text: str
    language: str
    confidence: float
    segments: list[dict] = field(default_factory=list)
    provider: str = "fake"


class STTError(Exception):
    pass


class SpeechToText(Protocol):
    name: str

    async def transcribe(
        self, audio: bytes, mime: str, lang_hint: str, *, duration_s: float | None = None,
        client_transcript: str | None = None, listing_id=None,
    ) -> Transcript: ...


def _ext(mime: str) -> str:
    return {"audio/webm": "webm", "audio/ogg": "ogg", "audio/mp4": "m4a", "audio/mpeg": "mp3",
            "audio/wav": "wav", "audio/x-wav": "wav", "audio/aac": "aac"}.get(mime.split(";")[0], "webm")


class WhisperSTT:
    name = "whisper"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def transcribe(self, audio, mime, lang_hint, *, duration_s=None, client_transcript=None, listing_id=None):
        from app.core.appconfig import DEFAULTS

        minutes = max(1.0, (duration_s or 60) / 60)
        files = {"file": (f"audio.{_ext(mime)}", audio, mime.split(";")[0])}
        data = {"model": get_settings().openai_stt_model, "response_format": "verbose_json"}
        if lang_hint:
            data["language"] = lang_hint
        async with track_call("stt", "whisper.transcribe", cost_inr=DEFAULTS["costs.v1"]["stt.minute"] * minutes, listing_id=listing_id):
            async with httpx.AsyncClient(timeout=httpx.Timeout(90.0, connect=10.0)) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    data=data,
                    files=files,
                )
            if resp.status_code >= 400:
                raise STTError(f"whisper {resp.status_code}: {resp.text[:200]}")
        body = resp.json()
        segments = body.get("segments") or []
        if segments:
            conf = sum(math.exp(min(0.0, s.get("avg_logprob", -0.5))) for s in segments) / len(segments)
        else:
            conf = 0.7
        lang = body.get("language") or lang_hint
        lang = {"hindi": "hi", "english": "en", "punjabi": "pa", "marathi": "mr", "gujarati": "gu",
                "urdu": "ur", "tamil": "ta", "malayalam": "ml"}.get(str(lang).lower(), lang)
        return Transcript(
            text=(body.get("text") or "").strip(),
            language=lang,
            confidence=round(conf, 3),
            segments=[{"start": s.get("start"), "end": s.get("end"), "text": s.get("text"),
                       "confidence": round(math.exp(min(0.0, s.get("avg_logprob", -0.5))), 3)} for s in segments],
            provider="whisper",
        )


class GeminiSTT:
    name = "gemini"

    async def transcribe(self, audio, mime, lang_hint, *, duration_s=None, client_transcript=None, listing_id=None):
        from app.providers.llm import get_llm

        try:
            result = await get_llm().generate_json(
                "Transcribe this voice note verbatim in the language it is spoken in (the speaker's UI language "
                f"is '{lang_hint}'). Do not translate or summarise. Return JSON with `text`, `language` (ISO 639-1) "
                "and `confidence` between 0 and 1.",
                schema={
                    "type": "object",
                    "properties": {"text": {"type": "string"}, "language": {"type": "string"}, "confidence": {"type": "number"}},
                    "required": ["text", "language"],
                },
                purpose="transcribe",
                audio=(audio, mime.split(";")[0]),
                fake_context={"fallback_text": client_transcript or "", "lang": lang_hint},
                listing_id=listing_id,
            )
            return Transcript(
                text=(result.get("text") or "").strip(),
                language=result.get("language") or lang_hint,
                confidence=float(result.get("confidence") or 0.75),
                provider="gemini",
            )
        except Exception:
            if client_transcript:
                return Transcript(
                    text=client_transcript.strip(),
                    language=lang_hint,
                    confidence=0.7,
                    provider="browser",
                )
            raise


class FakeSTT:
    name = "fake"

    async def transcribe(self, audio, mime, lang_hint, *, duration_s=None, client_transcript=None, listing_id=None):
        text = (client_transcript or "").strip()
        return Transcript(
            text=text,
            language=lang_hint,
            confidence=0.7 if text else 0.0,
            provider="browser" if text else "fake",
        )


_stt: SpeechToText | None = None


def get_stt() -> SpeechToText:
    global _stt
    if _stt is None:
        s = get_settings()
        choice = s.stt_provider
        if choice == "auto":
            project = s.vertex_project or os.environ.get("VERTEX_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT")
            if project or s.gemini_api_key:
                choice = "gemini"
            elif s.openai_api_key:
                choice = "whisper"
            else:
                choice = "fake"
        _stt = {"whisper": lambda: WhisperSTT(s.openai_api_key), "gemini": GeminiSTT, "vertex": GeminiSTT, "fake": FakeSTT}[choice]()
    return _stt


def set_stt(stt: SpeechToText | None) -> None:
    global _stt
    _stt = stt
