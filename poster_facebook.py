"""
poster_facebook.py — Poster generator khusus Facebook / OG Web (1200x630).

Berisi:
- generate_landscape_bytes()  : Render poster FB/OG ke BytesIO (in-memory)

Status: DIBUAT (TODO: Belum diaktifkan di main.py)
"""

from __future__ import annotations

import io
from typing import Any, Optional

from PIL import Image

from poster_common import (
    ACCENT_BLUE,
    ACCENT_GOLD,
    TAG_BG,
    TEXT_BLUE,
    TEXT_DARK,
    TEXT_GRAY,
    draw_icon_briefcase,
    draw_icon_building,
    draw_icon_globe,
    draw_icon_pin,
    draw_modern_background,
    fetch_image_from_url,
    get_font,
    get_text_width,
    make_qr_card,
    wrap_text,
)

# ─── Type Aliases ─────────────────────────────────────────────────────────────

JobDocument = dict[str, Any]

# ─── LAYOUT FACEBOOK / OG WEB (1200 x 630) ──────────────────────────────────


def generate_landscape_bytes(job: JobDocument) -> Optional[io.BytesIO]:
    """Render poster Facebook/OG Web (1200x630) langsung ke dalam memori.

    Args:
        job: Dokumen loker dari MongoDB.

    Returns:
        BytesIO berisi gambar PNG, atau None jika gagal.
    """
    try:
        company: str = job.get("company", "Perusahaan")
        location: str = job.get("location", "Indonesia")
        slug: str = job.get("slug", "")
        image_url: str = job.get("image_url", "")
        job_url: str = f"https://www.nyarikerja.online/lowongan/{slug}"

        # Ambil posisi pertama sebagai judul
        positions: list[dict[str, str]] = job.get("jobs", [])
        title: str = "Lowongan Kerja Terbaru"
        if positions:
            first_pos: str = positions[0].get("position", "")
            if len(positions) > 1:
                title = f"{first_pos} & {len(positions) - 1} Posisi Lainnya"
            elif first_pos:
                title = first_pos

        # Download logo (ukuran kecil)
        logo_img: Optional[Image.Image] = (
            fetch_image_from_url(image_url, size=(100, 100)) if image_url else None
        )

        # Buat QR Code
        qr_img: Image.Image = make_qr_card(job_url, size=140)

        W: int = 1200
        H: int = 630
        img = Image.new("RGB", (W, H))
        draw = draw_modern_background(img, W, H)

        f_brand = get_font(18, "semibold")
        f_hiring = get_font(18, "bold")
        f_title = get_font(48, "bold")
        f_comp = get_font(26, "medium")
        f_loc = get_font(22, "regular")

        tx: int = 80  # Margin kiri
        cy: int = 80

        # Brand Top Left (with globe icon)
        brand_txt: str = "nyarikerja.online"
        icon_sz: int = 18
        draw_icon_globe(draw, tx + icon_sz // 2, cy + 10, icon_sz, ACCENT_BLUE)
        draw.text((tx + icon_sz + 8, cy), brand_txt, fill=ACCENT_BLUE, font=f_brand)
        cy += 55

        # Hiring Tag (with briefcase icon)
        tag_txt: str = "WE ARE HIRING"
        h_w: int = get_text_width(tag_txt, f_hiring, draw)
        bc_sz: int = 18
        tag_total: int = bc_sz + 8 + h_w
        tag_pad_x: int = 18
        tag_pad_y: int = 10
        tag_x: int = tx
        tag_y: int = cy
        tag_right: int = tag_x + tag_total + tag_pad_x * 2
        tag_bottom: int = tag_y + bc_sz + tag_pad_y * 2
        draw.rounded_rectangle([tag_x, tag_y, tag_right, tag_bottom],
                               radius=20, fill=TAG_BG)
        icon_x: int = tag_x + tag_pad_x
        draw_icon_briefcase(draw, icon_x + bc_sz // 2, tag_y + tag_pad_y + bc_sz // 2,
                            bc_sz, (255, 255, 255))
        draw.text((icon_x + bc_sz + 8, tag_y + tag_pad_y), tag_txt,
                  fill=TEXT_BLUE, font=f_hiring)
        cy = tag_bottom + 25

        # Title
        t_lines: list[str] = wrap_text(title, f_title, W - 450, draw)
        for line in t_lines:
            draw.text((tx, cy), line, fill=TEXT_DARK, font=f_title)
            cy += 60
        cy += 15

        # Company (with building icon)
        c_icon_sz: int = 20
        draw_icon_building(draw, tx + c_icon_sz // 2, cy + 13, c_icon_sz, ACCENT_GOLD)
        draw.text((tx + c_icon_sz + 10, cy), company, fill=TEXT_GRAY, font=f_comp)
        cy += 45

        # Location (with pin icon)
        p_icon_sz: int = 18
        draw_icon_pin(draw, tx + p_icon_sz // 2, cy + 8, p_icon_sz, ACCENT_BLUE)
        draw.text((tx + p_icon_sz + 8, cy), location, fill=TEXT_GRAY, font=f_loc)

        # Bagian Kanan: QR Code & Logo
        right_center: int = W - 220

        # Logo di pojok kanan atas
        if logo_img:
            logo_w, logo_h = logo_img.size
            logo_margin: int = 45
            img.paste(logo_img, (W - logo_w - logo_margin, logo_margin + 6), logo_img)

        qr_w, qr_h = qr_img.size
        img.paste(qr_img, (right_center - (qr_w // 2), H - qr_h - 100), qr_img)

        cta: str = "Scan untuk Melamar"
        f_cta = get_font(16, "semibold")
        cta_w: int = get_text_width(cta, f_cta, draw)
        draw.text((right_center - (cta_w // 2), H - 80), cta, fill=TEXT_GRAY, font=f_cta)

        # Simpan ke BytesIO
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        buffer.seek(0)
        return buffer

    except Exception as e:
        print(f"❌ Gagal render poster Facebook: {e}")
        return None
