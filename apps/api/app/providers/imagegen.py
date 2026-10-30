"""Image generation provider (Google Gemini) for catalogue shots.

Real: Gemini image generation/editing with Nano Banana Pro (`gemini-3-pro-image`),
using real artisan reference photos to preserve product identity.
Outputs 2K images at 4:5 aspect ratio.

Fake: Deterministic PIL compositing onto a 4:5 white canvas for tests and offline development.
"""

from __future__ import annotations

import asyncio
import os
from typing import Protocol

from app.core.audit import track_call
from app.core.config import get_settings


class ImageGenError(Exception):
    pass


class ImageGen(Protocol):
    name: str

    async def edit(
        self,
        prompt: str,
        images: list[bytes],
        *,
        aspect_ratio: str = "4:5",
        purpose: str = "ai_image",
        listing_id=None,
    ) -> bytes: ...


def _mime_for_bytes(data: bytes) -> str:
    if data.startswith(b"\x89PNG"):
        return "image/png"
    if data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


class GeminiImageGen:
    name = "gemini"

    def __init__(
        self,
        *,
        vertex_project: str | None = None,
        location: str | None = None,
        api_key: str | None = None,
        credentials=None,
    ):
        from google import genai

        s = get_settings()
        self.vertex_project = vertex_project
        self.location = location or s.vertex_image_location
        if vertex_project:
            self.client = genai.Client(
                vertexai=True,
                project=vertex_project,
                location=self.location,
                credentials=credentials,
            )
        else:
            self.client = genai.Client(api_key=api_key or s.gemini_api_key)

    async def edit(
        self,
        prompt: str,
        images: list[bytes],
        *,
        aspect_ratio: str = "4:5",
        purpose: str = "ai_image",
        listing_id=None,
    ) -> bytes:
        from google.genai import types

        from app.core.appconfig import DEFAULTS

        s = get_settings()
        model = s.gemini_model_image

        image_parts = []
        for img in images:
            mime = _mime_for_bytes(img)
            image_parts.append(types.Part.from_bytes(data=img, mime_type=mime))

        contents = [*image_parts, prompt]
        # TEXT+IMAGE: Pro sometimes "thinks aloud" before the image; IMAGE-only then returns no inline data.
        config = types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],
            image_config=types.ImageConfig(aspect_ratio=aspect_ratio, image_size="2K"),
        )

        cost = DEFAULTS["costs.v1"].get("gemini.image", 11.5)
        try:
            async with track_call("gemini", purpose, cost_inr=cost, listing_id=listing_id):
                resp = await asyncio.wait_for(
                    self.client.aio.models.generate_content(
                        model=model,
                        contents=contents,
                        config=config,
                    ),
                    timeout=150,
                )
            for part in resp.parts or []:
                if part.inline_data and part.inline_data.data:
                    return part.inline_data.data
            raise ImageGenError(f"no inline image in gemini response: {resp}")
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("Gemini ImageGen unavailable (%s); falling back to deterministic shot compositor", exc)
            return await FakeImageGen().edit(prompt, images, aspect_ratio=aspect_ratio, purpose=purpose, listing_id=listing_id)


class FakeImageGen:
    name = "fake"

    async def edit(
        self,
        prompt: str,
        images: list[bytes],
        *,
        aspect_ratio: str = "4:5",
        purpose: str = "ai_image",
        listing_id=None,
    ) -> bytes:
        from io import BytesIO

        from PIL import Image

        canvas_w, canvas_h = 800, 1000
        canvas = Image.new("RGB", (canvas_w, canvas_h), (255, 255, 255))
        if images:
            with Image.open(BytesIO(images[0])) as img:
                img = img.convert("RGB")
                img.thumbnail((canvas_w, canvas_h), Image.Resampling.LANCZOS)
                paste_x = (canvas_w - img.width) // 2
                paste_y = (canvas_h - img.height) // 2
                canvas.paste(img, (paste_x, paste_y))
        buf = BytesIO()
        canvas.save(buf, format="JPEG", quality=90)
        return buf.getvalue()


_imagegen: ImageGen | None = None


def get_imagegen() -> ImageGen:
    global _imagegen
    if _imagegen is None:
        s = get_settings()
        if s.env == "test" or s.imagegen_backend == "fake":
            return FakeImageGen()
        backend = s.imagegen_backend
        project = s.vertex_project or os.environ.get("VERTEX_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT")
        if backend == "gemini" and s.gemini_api_key:
            _imagegen = GeminiImageGen(api_key=s.gemini_api_key)
        elif backend == "vertex" and project:
            _imagegen = GeminiImageGen(vertex_project=project, location=s.vertex_image_location)
        elif project and backend != "gemini":
            _imagegen = GeminiImageGen(vertex_project=project, location=s.vertex_image_location)
        elif s.gemini_api_key:
            _imagegen = GeminiImageGen(api_key=s.gemini_api_key)
        else:
            _imagegen = FakeImageGen()
    return _imagegen


def set_imagegen(gen: ImageGen | None) -> None:
    global _imagegen
    _imagegen = gen
