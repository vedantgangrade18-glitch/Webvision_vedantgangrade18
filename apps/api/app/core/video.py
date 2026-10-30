"""Video helpers built on ffmpeg/ffprobe (installed in the worker image).

Without ffmpeg (bare local dev) the functions degrade gracefully: duration comes from the
client, keyframes are empty, the fingerprint is the file hash (exact-duplicate detection
only) and the original file is used as the analysis proxy when it is small enough.
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

from app.core.imaging import hamming, phash


def has_ffmpeg() -> bool:
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def _run(cmd: list[str], timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, timeout=timeout, check=False)


async def probe_duration(data: bytes) -> float | None:
    if not has_ffmpeg():
        return None

    def _do():
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "in"
            src.write_bytes(data)
            res = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(src)], 60)
            try:
                return float(json.loads(res.stdout)["format"]["duration"])
            except (KeyError, ValueError, json.JSONDecodeError):
                return None

    return await asyncio.to_thread(_do)


async def keyframes(data: bytes, max_frames: int = 120) -> list[Image.Image]:
    """1 fps frames, capped at `max_frames`, 512 px wide. Audio is ignored (privacy)."""
    if not has_ffmpeg():
        return []

    def _do():
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "in"
            src.write_bytes(data)
            _run(["ffmpeg", "-v", "error", "-i", str(src), "-an", "-vf", "fps=1,scale=512:-2",
                  "-frames:v", str(max_frames), str(Path(tmp) / "f%04d.jpg")])
            frames = []
            for p in sorted(Path(tmp).glob("f*.jpg")):
                img = Image.open(p)
                img.load()
                frames.append(img.convert("RGB"))
            return frames

    return await asyncio.to_thread(_do)


async def proxy(data: bytes, max_bytes: int = 15 * 1024 * 1024) -> tuple[bytes, str] | None:
    """Low-res (360p, 1 fps-friendly, no audio) MP4 proxy for the LLM."""
    if not has_ffmpeg():
        return (data, "video/mp4") if len(data) <= max_bytes else None

    def _do():
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp) / "in", Path(tmp) / "out.mp4"
            src.write_bytes(data)
            _run(["ffmpeg", "-v", "error", "-i", str(src), "-an", "-vf", "scale=-2:360,fps=5", "-c:v", "libx264",
                  "-preset", "veryfast", "-crf", "32", "-t", "300", str(dst)])
            if dst.exists() and dst.stat().st_size <= max_bytes:
                return dst.read_bytes(), "video/mp4"
            return None

    return await asyncio.to_thread(_do)


async def poster(data: bytes) -> bytes | None:
    frames = await keyframes(data, max_frames=2)
    if not frames:
        return None
    buf = io.BytesIO()
    frames[-1].save(buf, "JPEG", quality=80)
    return buf.getvalue()


def fingerprint(frames: list[Image.Image], data: bytes) -> bytes:
    """Sequence of keyframe pHashes (8 bytes each); falls back to sha256 of the file."""
    if frames:
        return b"PH" + b"".join(bytes.fromhex(phash(f)) for f in frames)
    return b"SH" + hashlib.sha256(data).digest()


def fingerprint_similarity(a: bytes | None, b: bytes | None) -> float:
    """0–1. pHash sequences: share of frames in `a` with a near match (≤ 10 bits) in `b`."""
    if not a or not b or a[:2] != b[:2]:
        return 0.0
    if a[:2] == b"SH":
        return 1.0 if a == b else 0.0
    fa = [a[i:i + 8].hex() for i in range(2, len(a), 8)]
    fb = [b[i:i + 8].hex() for i in range(2, len(b), 8)]
    if not fa or not fb:
        return 0.0
    hits = sum(1 for x in fa if min(hamming(x, y) for y in fb) <= 10)
    return hits / len(fa)
