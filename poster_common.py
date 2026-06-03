"""
poster_common.py — Shared utilities untuk semua poster generator.

Berisi:
- Konstanta warna (Design System)
- Font loader (Inter + fallback)
- Ikon vektor (pin, gedung, koper, globe)
- Text wrapping & width helper
- Logo fetcher dari URL
- QR Code card generator
- Background renderer (gradien, geometris, dekorasi)

File ini TIDAK menghasilkan gambar apapun. File ini hanya menyediakan
"alat-alat lukis" yang digunakan oleh poster_telegram.py, poster_instagram.py,
dan poster_facebook.py.
"""

from __future__ import annotations

import io
import os
from typing import Optional

import qrcode
import requests
from PIL import Image, ImageDraw, ImageFont

# ─── DESIGN SYSTEM (Warna) ──────────────────────────────────────────────────

BG_TOP: tuple[int, int, int] = (255, 255, 255)
BG_BOTTOM: tuple[int, int, int] = (237, 242, 250)
ACCENT_BLUE: tuple[int, int, int] = (25, 70, 155)
ACCENT_GOLD: tuple[int, int, int] = (184, 156, 100)
ACCENT_LIGHT: tuple[int, int, int] = (234, 240, 250)
TAG_BG: tuple[int, int, int] = (25, 70, 155)
TEXT_DARK: tuple[int, int, int] = (20, 30, 50)
TEXT_GRAY: tuple[int, int, int] = (80, 95, 115)
TEXT_BLUE: tuple[int, int, int] = (255, 255, 255)
GOLD_STRIP: tuple[int, int, int] = (194, 166, 110)
BORDER_SUBTLE: tuple[int, int, int] = (210, 218, 230)

# ─── FONT SYSTEM ─────────────────────────────────────────────────────────────

_FONT_DIR: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
FONT_INTER: str = os.path.join(_FONT_DIR, "Inter-Variable.ttf")
FONT_BOLD_FALLBACK: str = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG_FALLBACK: str = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

_WEIGHT_MAP: dict[str, int] = {"regular": 400, "medium": 500, "semibold": 600, "bold": 700}


def get_font(size: int, weight: str = "regular") -> ImageFont.FreeTypeFont:
    """Memuat font Inter dengan berat tertentu. Fallback ke DejaVu."""
    axis_val: int = _WEIGHT_MAP.get(weight, 400)
    try:
        font = ImageFont.truetype(FONT_INTER, size)
        font.set_variation_by_axes([size, axis_val])
        return font
    except Exception:
        fb: str = FONT_BOLD_FALLBACK if weight in ("bold", "semibold") else FONT_REG_FALLBACK
        try:
            return ImageFont.truetype(fb, size)
        except IOError:
            return ImageFont.load_default()


# ─── ICON DRAWING (Vektor, digambar langsung dengan PIL) ─────────────────────

def draw_icon_pin(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: tuple) -> None:
    """Menggambar ikon pin lokasi (location marker)."""
    r: int = size // 2
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    tri_h: int = int(r * 1.3)
    draw.polygon([
        (cx - r * 0.55, cy + r * 0.4),
        (cx + r * 0.55, cy + r * 0.4),
        (cx, cy + r + tri_h)
    ], fill=color)
    ir: int = int(r * 0.38)
    draw.ellipse([cx - ir, cy - ir, cx + ir, cy + ir], fill=(255, 255, 255))


def draw_icon_building(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: tuple) -> None:
    """Menggambar ikon gedung (company/corporate)."""
    w: int = size
    h: int = int(size * 1.2)
    x0: int = cx - w // 2
    y0: int = cy - h // 2
    draw.rectangle([x0, y0, x0 + w, y0 + h], fill=color)
    win_w: int = w // 5
    win_h: int = h // 6
    gap_x: int = (w - 2 * win_w) // 3
    gap_y: int = (h - 3 * win_h) // 4
    for row in range(3):
        for col in range(2):
            wx: int = x0 + gap_x + col * (win_w + gap_x)
            wy: int = y0 + gap_y + row * (win_h + gap_y)
            draw.rectangle([wx, wy, wx + win_w, wy + win_h], fill=(255, 255, 255))
    dw: int = w // 4
    dh: int = h // 4
    draw.rectangle([cx - dw // 2, y0 + h - dh, cx + dw // 2, y0 + h], fill=(255, 255, 255))


def draw_icon_briefcase(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: tuple) -> None:
    """Menggambar ikon koper/briefcase (job/hiring)."""
    w: int = size
    h: int = int(size * 0.75)
    x0: int = cx - w // 2
    y0: int = cy - h // 2
    r: int = size // 8
    draw.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=r, fill=color)
    handle_w: int = w // 3
    handle_h: int = h // 4
    hx: int = cx - handle_w // 2
    hy: int = y0 - handle_h
    draw.rounded_rectangle([hx, hy, hx + handle_w, y0 + 2], radius=r // 2,
                           outline=color, width=max(2, size // 12))
    stripe_h: int = max(2, size // 10)
    draw.rectangle([x0, cy - stripe_h // 2, x0 + w, cy + stripe_h // 2],
                   fill=(255, 255, 255))


def draw_icon_globe(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: tuple) -> None:
    """Menggambar ikon globe/web."""
    r: int = size // 2
    lw: int = max(2, size // 12)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=lw)
    er: int = int(r * 0.5)
    draw.ellipse([cx - er, cy - r, cx + er, cy + r], outline=color, width=lw)
    draw.line([(cx - r, cy), (cx + r, cy)], fill=color, width=lw)
    off: int = int(r * 0.55)
    draw.line([(cx - r + 3, cy - off), (cx + r - 3, cy - off)], fill=color, width=max(1, lw - 1))
    draw.line([(cx - r + 3, cy + off), (cx + r - 3, cy + off)], fill=color, width=max(1, lw - 1))


# ─── TEXT HELPERS ─────────────────────────────────────────────────────────────

def get_text_width(text: str, font: ImageFont.FreeTypeFont, draw: ImageDraw.ImageDraw) -> int:
    """Mendapatkan lebar teks untuk centering."""
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
    """Memecah teks ke baris baru jika melebihi lebar maksimum."""
    words: list[str] = text.split()
    lines: list[str] = []
    cur: str = ""
    for w in words:
        t: str = f"{cur} {w}".strip()
        if get_text_width(t, font, draw) <= max_width:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


# ─── LOGO FETCHER ─────────────────────────────────────────────────────────────

def fetch_image_from_url(url: str, size: tuple[int, int] = (100, 100)) -> Optional[Image.Image]:
    """Mengunduh gambar logo dari URL dan menambahkan styling (card/shadow)."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        img = Image.open(io.BytesIO(response.content)).convert("RGBA")
        img = img.resize(size, Image.LANCZOS)

        pad: int = 20
        bg_size: int = size[0] + pad * 2
        frame = Image.new("RGBA", (bg_size, bg_size), (0, 0, 0, 0))
        fd = ImageDraw.Draw(frame)

        fd.rounded_rectangle([2, 2, bg_size, bg_size], radius=15, fill=(0, 0, 0, 25))
        fd.rounded_rectangle([0, 0, bg_size - 2, bg_size - 2], radius=15,
                             fill=(255, 255, 255, 255), outline=BORDER_SUBTLE, width=1)

        frame.paste(img, (pad, pad), img)
        return frame
    except Exception as e:
        print(f"⚠️ Gagal memuat logo dari URL: {e}")
        return None


# ─── QR CODE CARD ─────────────────────────────────────────────────────────────

def make_qr_card(url: str, size: int = 150) -> Image.Image:
    """Membuat QR code dengan frame berbentuk kartu."""
    qr = qrcode.QRCode(version=1, box_size=10, border=0)
    qr.add_data(url)
    qr.make(fit=True)
    raw = qr.make_image(fill_color=TEXT_DARK, back_color="white").convert("RGBA")
    raw = raw.resize((size, size), Image.NEAREST)

    pad: int = 20
    fs: int = size + pad * 2
    frame = Image.new("RGBA", (fs, fs), (0, 0, 0, 0))
    fd = ImageDraw.Draw(frame)
    fd.rounded_rectangle([3, 3, fs, fs], radius=16, fill=(0, 0, 0, 22))
    fd.rounded_rectangle([0, 0, fs - 3, fs - 3], radius=16,
                         fill=(255, 255, 255, 255), outline=BORDER_SUBTLE, width=1)
    frame.paste(raw, (pad, pad), raw)
    return frame


# ─── BACKGROUND RENDERER ─────────────────────────────────────────────────────

def _draw_gradient(draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
    """Menggambar gradien vertikal halus dari putih ke biru muda."""
    for y in range(height):
        ratio: float = y / height
        r: int = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * ratio)
        g: int = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * ratio)
        b: int = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))


def _draw_diagonal_grid(draw: ImageDraw.ImageDraw, width: int, height: int, spacing: int = 60) -> None:
    """Menggambar garis diagonal tipis sebagai pola latar subtle."""
    line_color: tuple = (215, 222, 235, 35)
    for offset in range(-height, width + height, spacing):
        draw.line([(offset, height), (offset + height, 0)], fill=line_color, width=1)


def _draw_corner_flourish(draw: ImageDraw.ImageDraw, width: int, height: int, corner: str = "top-right") -> None:
    """Menggambar dekorasi sudut geometris elegant."""
    gold_a: tuple = (*ACCENT_GOLD, 40)
    blue_a: tuple = (*ACCENT_BLUE, 20)

    if corner == "top-right":
        cx, cy = width, 0
        for i, r in enumerate([280, 220, 160]):
            c = gold_a if i % 2 == 0 else blue_a
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=c, width=2)
    elif corner == "bottom-left":
        cx, cy = 0, height
        for i, r in enumerate([250, 190]):
            c = gold_a if i % 2 == 0 else blue_a
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=c, width=2)


def draw_modern_background(img: Image.Image, width: int, height: int) -> ImageDraw.ImageDraw:
    """Latar belakang elegant professional: gradien halus, pola geometris,
       strip emas atas, dan dekorasi sudut."""
    draw = ImageDraw.Draw(img, "RGBA")

    _draw_gradient(draw, width, height)
    _draw_diagonal_grid(draw, width, height)
    _draw_corner_flourish(draw, width, height, "top-right")
    _draw_corner_flourish(draw, width, height, "bottom-left")

    draw.rectangle([0, 0, width, 6], fill=GOLD_STRIP)
    draw.rectangle([0, height - 4, width, height], fill=GOLD_STRIP)

    margin: int = 25
    draw.rounded_rectangle(
        [margin, margin + 6, width - margin, height - margin - 4],
        radius=0, outline=(*BORDER_SUBTLE, 60), width=1
    )

    return draw
