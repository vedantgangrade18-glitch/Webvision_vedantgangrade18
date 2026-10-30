"""Image toolkit: validation, EXIF (GPS never kept), quality gate, pHash, lightweight
embeddings, NON-generative enhancement, 4:5 / 1:1 variants, QR share images and the
printable tag sheet (Part 2 §6.3, §9.1, §9.3).

Policy (Part 1 §10): `enhance` only orients, crops, levels, white-balances and lightly
sharpens the artisan's own photo. Originals are kept privately for verification and the
Karu ID proof page; generative catalogue shots (Gemini) are handled via `imagegen` and
go in the gallery where the artisan can remove any of them.
"""

from __future__ import annotations

import io
import math
import os
from functools import lru_cache

import imagehash
import qrcode
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps, ImageStat, features
from qrcode.constants import ERROR_CORRECT_Q

from app.core.translit import has_indic, to_latin

Image.MAX_IMAGE_PIXELS = 60_000_000

# Brand colours (Part 1 §9.2)
INDIGO = (31, 42, 107)
KHADI = (251, 248, 242)
HALDI = (227, 167, 47)
PEACOCK = (17, 117, 107)
UNVERIFIED = (122, 115, 107)
INK = (30, 26, 22)
WHITE = (255, 255, 255)


# ---- type sniffing ---------------------------------------------------------------------

def sniff_mime(data: bytes) -> str | None:
    head = data[:64]
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return "audio/wav"
    if head[4:8] == b"ftyp":
        brand = head[8:12]
        if brand in (b"heic", b"heix", b"mif1", b"msf1"):
            return "image/heic"
        if brand in (b"avif", b"avis"):
            return "image/avif"
        if brand in (b"M4A ", b"M4B "):
            return "audio/mp4"
        if brand == b"qt  ":
            return "video/quicktime"
        return "video/mp4"  # isom, mp41, mp42, 3gp4 … (iOS voice notes are also mp4 → treated per declared kind)
    if head.startswith(b"\x1a\x45\xdf\xa3"):
        return "video/webm"  # also audio/webm (MediaRecorder) – same container
    if head.startswith(b"OggS"):
        return "audio/ogg"
    if head.startswith(b"ID3") or head[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return "audio/mpeg"
    if head.startswith(b"%PDF"):
        return "application/pdf"
    return None


KIND_MIMES = {
    "photo": {"image/jpeg", "image/png", "image/webp", "image/avif"},
    "voice": {"video/webm", "audio/ogg", "audio/mp4", "video/mp4", "audio/mpeg", "audio/wav"},
    "video": {"video/mp4", "video/webm", "video/quicktime"},
    "document": {"application/pdf", "image/jpeg", "image/png"},
}


def kind_accepts(kind: str, sniffed: str | None) -> bool:
    return sniffed is not None and sniffed in KIND_MIMES.get(kind, set())


# ---- loading & metadata ------------------------------------------------------------------

def load_image(data: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(data))
    img.load()
    img = ImageOps.exif_transpose(img)
    if img.mode not in ("RGB", "L"):
        bg = Image.new("RGB", img.size, WHITE)
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA")
            bg.paste(img, mask=img.split()[-1])
            img = bg
        else:
            img = img.convert("RGB")
    elif img.mode == "L":
        img = img.convert("RGB")
    return img


_EXIF_KEEP = {271: "make", 272: "model", 305: "software", 306: "datetime", 36867: "datetime_original"}


def exif_summary(data: bytes) -> dict:
    """Keep a few non-identifying tags; record only *whether* GPS was present."""
    try:
        img = Image.open(io.BytesIO(data))
        exif = img.getexif()
    except Exception:  # noqa: BLE001
        return {}
    out = {name: str(exif.get(tag)) for tag, name in _EXIF_KEEP.items() if exif.get(tag)}
    try:
        sub = exif.get_ifd(0x8769)
        if sub.get(36867):
            out["datetime_original"] = str(sub.get(36867))
    except Exception:  # noqa: BLE001
        pass
    out["had_gps"] = bool(exif.get(0x8825))
    return out


def quality(img: Image.Image) -> dict:
    """Blur (variance of Laplacian), brightness, resolution → simple gate (Part 2 §7.1)."""
    small = img.copy()
    small.thumbnail((512, 512))
    gray = small.convert("L")
    lap = gray.filter(ImageFilter.Kernel((3, 3), [0, 1, 0, 1, -4, 1, 0, 1, 0], scale=1, offset=128))
    blur = ImageStat.Stat(lap).var[0]
    brightness = ImageStat.Stat(gray).mean[0]
    min_side = min(img.size)
    issues = []
    if blur < 40:
        issues.append("blurry")
    if brightness < 45:
        issues.append("too_dark")
    if brightness > 235:
        issues.append("too_bright")
    if min_side < 300:
        issues.append("low_resolution")
    return {"blur": round(blur, 1), "brightness": round(brightness, 1), "min_side": min_side,
            "ok": not issues, "issues": issues}


def phash(img: Image.Image) -> str:
    return str(imagehash.phash(img))


def hamming(a: str | None, b: str | None) -> int:
    if not a or not b:
        return 64
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def lite_embedding(img: Image.Image) -> list[float]:
    """Cheap, deterministic 336-d image descriptor (HSV histogram + 16×16 luminance + edges).
    Stands in for SigLIP/CLIP until the `ml` worker image is deployed (Part 2 §2)."""
    small = img.convert("RGB").resize((64, 64))
    hsv = small.convert("HSV")
    hist = [0.0] * 64
    for h, s, v in hsv.getdata():
        hist[(h * 4 // 256) * 16 + (s * 4 // 256) * 4 + (v * 4 // 256)] += 1
    total = sum(hist) or 1
    hist = [x / total for x in hist]
    lum = [p / 255 for p in img.convert("L").resize((16, 16)).getdata()]
    mean = sum(lum) / len(lum)
    lum = [x - mean for x in lum]
    edges = img.convert("L").resize((64, 64)).filter(ImageFilter.FIND_EDGES).resize((4, 4))
    edge = [p / 255 for p in edges.getdata()]
    vec = [x * 3 for x in hist] + lum + edge
    norm = math.sqrt(sum(x * x for x in vec)) or 1
    return [round(x / norm, 5) for x in vec]


def cosine(a: list[float] | None, b: list[float] | None) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b, strict=True))


# ---- enhancement & variants ----------------------------------------------------------------

def _gray_world(img: Image.Image, strength: float = 0.5) -> Image.Image:
    r, g, b = (ImageStat.Stat(img).mean[i] for i in range(3))
    avg = (r + g + b) / 3 or 1
    gains = [1 + strength * (avg / max(c, 1) - 1) for c in (r, g, b)]
    gains = [min(1.25, max(0.8, x)) for x in gains]
    channels = [ch.point(lambda v, k=k: min(255, int(v * k))) for ch, k in zip(img.split(), gains, strict=True)]
    return Image.merge("RGB", channels)


def _subject_box(img: Image.Image) -> tuple[int, int, int, int]:
    """Bounding box of pixels that differ from the border colour (plain-background shots)."""
    small = img.copy()
    small.thumbnail((256, 256))
    sx, sy = img.width / small.width, img.height / small.height
    gray = small.convert("L")
    w, h = gray.size
    border = [gray.getpixel((x, 0)) for x in range(w)] + [gray.getpixel((x, h - 1)) for x in range(w)]
    border += [gray.getpixel((0, y)) for y in range(h)] + [gray.getpixel((w - 1, y)) for y in range(h)]
    bg = sorted(border)[len(border) // 2]
    mask = gray.point(lambda v: 255 if abs(v - bg) > 28 else 0)
    box = mask.getbbox()
    if not box:
        return (0, 0, img.width, img.height)
    x0, y0, x1, y1 = box
    if (x1 - x0) * (y1 - y0) < 0.15 * w * h:  # tiny subject → probably noise; keep full frame
        return (0, 0, img.width, img.height)
    pad = 0.06
    return (
        max(0, int((x0 - pad * w) * sx)), max(0, int((y0 - pad * h) * sy)),
        min(img.width, int((x1 + pad * w) * sx)), min(img.height, int((y1 + pad * h) * sy)),
    )


def enhance(img: Image.Image) -> Image.Image:
    out = img.convert("RGB")
    out = out.crop(_subject_box(out))
    out = ImageOps.autocontrast(out, cutoff=1, preserve_tone=True)
    out = _gray_world(out)
    out = out.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=3))
    return out


def crop_to_ratio(img: Image.Image, rw: int, rh: int) -> Image.Image:
    target = rw / rh
    w, h = img.size
    if w / h > target:
        nw = int(h * target)
        left = (w - nw) // 2
        return img.crop((left, 0, left + nw, h))
    nh = int(w / target)
    top = max(0, (h - nh) // 2)
    return img.crop((0, top, w, top + nh))


def encode(img: Image.Image, fmt: str = "JPEG", quality_: int = 82) -> bytes:
    buf = io.BytesIO()
    if fmt == "WEBP":
        img.save(buf, "WEBP", quality=quality_, method=4)
    else:
        img.convert("RGB").save(buf, "JPEG", quality=quality_, optimize=True, progressive=True)
    return buf.getvalue()


def variants(img: Image.Image, sizes: tuple[int, ...] = (400, 800, 1600)) -> dict[str, bytes]:
    """4:5 and 1:1 crops keyed 400/800/1600 (capped at the photo width), WebP + JPEG. No EXIF is written."""
    out: dict[str, bytes] = {}
    for ratio_name, (rw, rh) in (("4x5", (4, 5)), ("1x1", (1, 1))):
        cropped = crop_to_ratio(img, rw, rh)
        for width_target in sizes:
            # Never upscale: a size larger than the photo is emitted at the photo's own width.
            width = min(width_target, cropped.width)
            height = int(width * rh / rw)
            resized = cropped.resize((width, height), Image.Resampling.LANCZOS)
            out[f"{width_target}_{ratio_name}.webp"] = encode(resized, "WEBP", 80)
            out[f"{width_target}_{ratio_name}.jpg"] = encode(resized, "JPEG", 82)
    return out


def compress_for_llm(img: Image.Image, max_side: int = 1024, quality: int = 80) -> bytes:
    small = img.copy()
    small.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    return encode(small, "JPEG", quality)


# ---- fonts & text ------------------------------------------------------------------------------

_FONT_CANDIDATES = {
    "sans": [
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/noto/NotoSans-Regular.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ],
    "sans_bold": [
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
        "/usr/share/fonts/noto/NotoSans-Bold.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ],
    "serif": [
        "/usr/share/fonts/truetype/noto/NotoSerif-Regular.ttf",
        "/usr/share/fonts/noto/NotoSerif-Regular.ttf",
        "C:/Windows/Fonts/georgia.ttf",
        "/System/Library/Fonts/Supplemental/Georgia.ttf",
    ],
    "indic": [
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
        "/usr/share/fonts/noto/NotoSansDevanagari-Regular.ttf",
        "C:/Windows/Fonts/Nirmala.ttc",
    ],
}


@lru_cache(maxsize=64)
def font(kind: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in _FONT_CANDIDATES.get(kind, []):
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default(size)


def safe_text(text: str) -> str:
    """Without libraqm Indic shaping breaks; fall back to a romanised form (Docker has raqm)."""
    if has_indic(text) and not features.check("raqm"):
        return to_latin(text).title()
    return text


def _fit(draw: ImageDraw.ImageDraw, text: str, kind: str, size: int, max_w: int) -> tuple[str, ImageFont.ImageFont]:
    text = safe_text(text)
    f = font("indic" if has_indic(text) else kind, size)
    while draw.textlength(text, font=f) > max_w and size > 14:
        size -= 2
        f = font("indic" if has_indic(text) else kind, size)
    if draw.textlength(text, font=f) > max_w:
        while text and draw.textlength(text + "…", font=f) > max_w:
            text = text[:-1]
        text += "…"
    return text, f


def make_qr(url: str, box_px: int) -> Image.Image:
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_Q, border=4, box_size=10)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color=INK, back_color=WHITE).convert("RGB")
    return img.resize((box_px, box_px), Image.Resampling.NEAREST)


def _woven_line(draw: ImageDraw.ImageDraw, x0: int, y: int, x1: int, color=HALDI) -> None:
    """The Karu woven motif: a thin over-under stitch line."""
    step = 14
    for i, x in enumerate(range(x0, x1, step)):
        if i % 2 == 0:
            draw.line([(x, y), (x + step - 4, y)], fill=color, width=3)
        else:
            draw.line([(x, y - 3), (x + step - 4, y + 3)], fill=color, width=2)


def render_share_image(
    photo: Image.Image | None,
    *,
    fmt: str,
    title: str,
    maker: str,
    verdict_label: str,
    verified: bool,
    short_url: str,
    qr_url: str | None,
) -> bytes:
    """Share images: 1080×1350 (4:5), 1080×1920 (9:16), 1200×630 (OG). `qr_url=None` → no QR."""
    sizes = {"4x5": (1080, 1350), "9x16": (1080, 1920), "og": (1200, 630)}
    W, H = sizes[fmt]
    band_h = {"4x5": 300, "9x16": 360, "og": 190}[fmt]
    canvas = Image.new("RGB", (W, H), KHADI)
    if photo is not None:
        if fmt == "og":
            pw = int(W * 0.5)
            pic = crop_to_ratio(photo, pw, H).resize((pw, H), Image.Resampling.LANCZOS)
            canvas.paste(pic, (0, 0))
        else:
            pic = crop_to_ratio(photo, W, H - band_h).resize((W, H - band_h), Image.Resampling.LANCZOS)
            canvas.paste(pic, (0, 0))
    draw = ImageDraw.Draw(canvas)
    pill_color = PEACOCK if verified else UNVERIFIED

    if fmt == "og":
        x0, y = int(W * 0.5) + 48, 60
        draw.text((x0, y), "KARU", font=font("serif", 44), fill=INDIGO)
        _woven_line(draw, x0, y + 70, W - 48)
        t, f = _fit(draw, title, "serif", 46, W - x0 - 48)
        draw.text((x0, y + 100), t, font=f, fill=INK)
        m, f2 = _fit(draw, maker, "sans", 30, W - x0 - 48)
        draw.text((x0, y + 170), m, font=f2, fill=(92, 85, 77))
        _pill(draw, (x0, y + 240), verdict_label, pill_color, 30)
        draw.text((x0, H - 80), short_url, font=font("sans", 26), fill=INDIGO)
    else:
        top = H - band_h
        draw.rectangle([0, top, W, H], fill=WHITE)
        _woven_line(draw, 0, top + 4, W, HALDI)
        pad = 48
        qr_size = band_h - 2 * 36 if qr_url else 0
        text_w = W - 2 * pad - (qr_size + 32 if qr_url else 0)
        y = top + 36
        draw.text((pad, y), "KARU", font=font("serif", 40), fill=INDIGO)
        y += 58
        t, f = _fit(draw, title, "serif", 40, text_w)
        draw.text((pad, y), t, font=f, fill=INK)
        y += 56
        m, f2 = _fit(draw, maker, "sans", 28, text_w)
        draw.text((pad, y), m, font=f2, fill=(92, 85, 77))
        y += 50
        _pill(draw, (pad, y), verdict_label, pill_color, 26)
        if qr_url:
            qr = make_qr(qr_url, qr_size)
            canvas.paste(qr, (W - pad - qr_size, top + 36))
            u, f3 = _fit(draw, short_url, "sans", 20, qr_size)
            draw.text((W - pad - qr_size, top + 36 + qr_size + 2), u, font=f3, fill=(92, 85, 77))
    return encode(canvas, "JPEG", 88)


def _pill(draw: ImageDraw.ImageDraw, xy: tuple[int, int], label: str, color, size: int) -> None:
    label = safe_text(label)
    f = font("indic" if has_indic(label) else "sans_bold", size)
    w = int(draw.textlength(label, font=f)) + size * 2 + 18
    h = int(size * 1.9)
    x, y = xy
    draw.rounded_rectangle([x, y, x + w, y + h], radius=h // 2, fill=color)
    # check mark / dot
    cx, cy = x + size, y + h // 2
    draw.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=WHITE)
    draw.text((x + size + 18, y + (h - size) // 2 - 4), label, font=f, fill=WHITE)


def render_tag_sheet(units: list[tuple[str, str]], *, title: str, maker: str, scan_local: str, scan_en: str) -> bytes:
    """A4 label sheet (3 × 7) at 200 dpi: unit QR → /k/KRU-…, code, short text. Returns PDF bytes."""
    dpi = 200
    W, H = int(8.27 * dpi), int(11.69 * dpi)
    cols, rows = 3, 7
    margin_x, margin_y = int(0.3 * dpi), int(0.5 * dpi)
    cell_w = (W - 2 * margin_x) // cols
    cell_h = (H - 2 * margin_y) // rows
    pages: list[Image.Image] = []
    per_page = cols * rows
    for start in range(0, max(1, len(units)), per_page):
        page = Image.new("RGB", (W, H), WHITE)
        d = ImageDraw.Draw(page)
        for i, (code, url) in enumerate(units[start:start + per_page]):
            cx = margin_x + (i % cols) * cell_w
            cy = margin_y + (i // cols) * cell_h
            d.rounded_rectangle([cx + 8, cy + 8, cx + cell_w - 8, cy + cell_h - 8], radius=18, outline=(189, 181, 170), width=2)
            q = cell_h - 60
            page.paste(make_qr(url, q), (cx + 18, cy + 30))
            tx = cx + 18 + q + 12
            tw = cell_w - (q + 48)
            d.text((tx, cy + 34), "KARU", font=font("serif", 30), fill=INDIGO)
            c, fc = _fit(d, code, "sans_bold", 22, tw)
            d.text((tx, cy + 78), c, font=fc, fill=INK)
            t, ft = _fit(d, title, "sans", 18, tw)
            d.text((tx, cy + 114), t, font=ft, fill=(92, 85, 77))
            m, fm = _fit(d, maker, "sans", 18, tw)
            d.text((tx, cy + 140), m, font=fm, fill=(92, 85, 77))
            s1, fs1 = _fit(d, scan_local, "sans", 16, tw)
            d.text((tx, cy + cell_h - 82), s1, font=fs1, fill=INDIGO)
            if scan_en != scan_local:
                s2, fs2 = _fit(d, scan_en, "sans", 16, tw)
                d.text((tx, cy + cell_h - 58), s2, font=fs2, fill=INDIGO)
        pages.append(page)
    buf = io.BytesIO()
    pages[0].save(buf, "PDF", resolution=dpi, save_all=True, append_images=pages[1:])
    return buf.getvalue()
