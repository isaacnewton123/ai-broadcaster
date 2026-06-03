"""
poster_instagram.py — Poster generator khusus Instagram Feed (1080x1080).

Berisi:
- generate_square_bytes()  : Render poster IG Feed ke BytesIO (in-memory)

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

# ─── LAYOUT INSTAGRAM FEED (1080 x 1080) ────────────────────────────────────


def generate_square_bytes(job: JobDocument) -> Optional[io.BytesIO]:
    """Render poster Instagram Feed (1080x1080) langsung ke dalam memori.

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

        # Download logo dari R2 (jika ada)
        logo_img: Optional[Image.Image] = (
            fetch_image_from_url(image_url, size=(160, 160)) if image_url else None
        )

        # Buat QR Code
        qr_img: Image.Image = make_qr_card(job_url, size=140)

        # Render poster ke dalam memori
        W: int = 1080
        H: int = 1080
        img = Image.new("RGB", (W, H))
        draw = draw_modern_background(img, W, H)

        f_brand = get_font(28, "semibold")
        f_hiring = get_font(30, "bold")
        f_title = get_font(72, "bold")
        f_comp = get_font(38, "medium")
        f_loc = get_font(32, "regular")

        # Brand Top (with globe icon)
        brand_txt: str = "nyarikerja.online"
        b_w: int = get_text_width(brand_txt, f_brand, draw)
        icon_sz: int = 26
        total_brand: int = icon_sz + 10 + b_w
        bx: int = (W - total_brand) // 2
        # Sedikit lebih naik dari versi Telegram
        draw_icon_globe(draw, bx + icon_sz // 2, 50 + 15, icon_sz, ACCENT_BLUE)
        draw.text((bx + icon_sz + 10, 50), brand_txt, fill=ACCENT_BLUE, font=f_brand)

        # Logo Center
        if logo_img:
            logo_w, logo_h = logo_img.size
            img.paste(logo_img, ((W - logo_w) // 2, 170), logo_img)

        # Cy disesuaikan lebih naik untuk IG Feed
        cy: int = 400

        # Hiring Tag (with briefcase icon)
        tag_txt: str = "WE ARE HIRING"
        h_w: int = get_text_width(tag_txt, f_hiring, draw)
        bc_sz: int = 26
        tag_total: int = bc_sz + 10 + h_w
        tag_pad_x: int = 30
        tag_pad_y: int = 14
        tag_x: int = (W - tag_total) // 2 - tag_pad_x
        tag_y: int = cy
        tag_right: int = tag_x + tag_total + tag_pad_x * 2
        tag_bottom: int = tag_y + bc_sz + tag_pad_y * 2
        draw.rounded_rectangle([tag_x, tag_y, tag_right, tag_bottom],
                               radius=27, fill=TAG_BG)
        icon_x: int = tag_x + tag_pad_x
        draw_icon_briefcase(draw, icon_x + bc_sz // 2, tag_y + tag_pad_y + bc_sz // 2,
                            bc_sz, (255, 255, 255))
        draw.text((icon_x + bc_sz + 10, tag_y + tag_pad_y), tag_txt,
                  fill=TEXT_BLUE, font=f_hiring)
        cy = tag_bottom + 30

        # Title
        t_lines: list[str] = wrap_text(title, f_title, W - 150, draw)
        for line in t_lines:
            lw: int = get_text_width(line, f_title, draw)
            draw.text(((W - lw) // 2, cy), line, fill=TEXT_DARK, font=f_title)
            cy += 85
        cy += 15

        # Company (with building icon)
        c_w: int = get_text_width(company, f_comp, draw)
        c_icon_sz: int = 28
        c_total: int = c_icon_sz + 12 + c_w
        c_x: int = (W - c_total) // 2
        draw_icon_building(draw, c_x + c_icon_sz // 2, cy + 19, c_icon_sz, ACCENT_GOLD)
        draw.text((c_x + c_icon_sz + 12, cy), company, fill=TEXT_GRAY, font=f_comp)
        cy += 65

        # Location (with pin icon)
        l_w: int = get_text_width(location, f_loc, draw)
        p_icon_sz: int = 24
        l_total: int = p_icon_sz + 10 + l_w
        l_x: int = (W - l_total) // 2
        draw_icon_pin(draw, l_x + p_icon_sz // 2, cy + 12, p_icon_sz, ACCENT_BLUE)
        draw.text((l_x + p_icon_sz + 10, cy), location, fill=TEXT_GRAY, font=f_loc)

        # QR Bottom
        qr_w, qr_h = qr_img.size
        qr_y: int = H - qr_h - 70
        img.paste(qr_img, ((W - qr_w) // 2, qr_y), qr_img)

        # Call to action text
        cta: str = "Scan QR untuk Melamar"
        f_cta = get_font(24, "semibold")
        cta_w: int = get_text_width(cta, f_cta, draw)
        draw.text(((W - cta_w) // 2, qr_y + qr_h + 20), cta, fill=TEXT_GRAY, font=f_cta)

        # Simpan ke BytesIO (memori virtual)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        buffer.seek(0)
        return buffer

    except Exception as e:
        print(f"❌ Gagal render poster Instagram: {e}")
        return None
