"""
telegram_publisher.py — Pengirim pesan ke Telegram Channel via HTTP Bot API.

Berisi:
- send_photo_with_caption()  : Kirim gambar + caption ke Channel
- send_text_only()           : Kirim pesan teks saja (fallback jika gambar gagal)

Menggunakan aiohttp agar non-blocking dan kompatibel dengan asyncio.
"""

from __future__ import annotations

import io
from typing import Any, Optional

import aiohttp

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_PUBLISH_CHANNEL
from logger import get_logger

logger = get_logger(__name__)

# ─── Telegram Bot API Base URL ────────────────────────────────────────────────

_BASE_URL: str = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


# ─── Kirim Foto + Caption ────────────────────────────────────────────────────

async def send_photo_with_caption(
    image_bytes: io.BytesIO,
    caption: str,
    filename: str = "poster.png",
) -> bool:
    """Kirim gambar poster + caption ke Channel Telegram.

    Args:
        image_bytes: Gambar dalam bentuk BytesIO (di memori, bukan file fisik).
        caption: Teks caption yang akan ditampilkan di bawah gambar.
        filename: Nama file gambar (hanya untuk metadata Telegram).

    Returns:
        True jika berhasil terkirim, False jika gagal.
    """
    url: str = f"{_BASE_URL}/sendPhoto"

    # Reset posisi baca BytesIO ke awal
    image_bytes.seek(0)

    data = aiohttp.FormData()
    data.add_field("chat_id", TELEGRAM_PUBLISH_CHANNEL)
    data.add_field("caption", caption[:1024])  # Telegram limit: 1024 karakter untuk caption foto
    data.add_field("parse_mode", "HTML")
    data.add_field(
        "photo",
        image_bytes,
        filename=filename,
        content_type="image/png",
    )

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                result: dict[str, Any] = await resp.json()
                if result.get("ok"):
                    logger.info(f"📤 Foto berhasil terkirim ke {TELEGRAM_PUBLISH_CHANNEL}")
                    return True
                else:
                    error_desc: str = result.get("description", "Unknown error")
                    logger.error(f"❌ Gagal kirim foto: {error_desc}")
                    return False
    except Exception as e:
        logger.error(f"❌ Exception saat mengirim foto: {e}", exc_info=True)
        return False


# ─── Kirim Teks Saja (Fallback) ──────────────────────────────────────────────

async def send_text_only(caption: str) -> bool:
    """Kirim pesan teks saja ke Channel Telegram (fallback jika poster gagal dirender).

    Args:
        caption: Teks pesan yang akan dikirim.

    Returns:
        True jika berhasil terkirim, False jika gagal.
    """
    url: str = f"{_BASE_URL}/sendMessage"

    payload: dict[str, str] = {
        "chat_id": TELEGRAM_PUBLISH_CHANNEL,
        "text": caption[:4096],  # Telegram limit: 4096 karakter untuk pesan teks
        "parse_mode": "HTML",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                result: dict[str, Any] = await resp.json()
                if result.get("ok"):
                    logger.info(f"📤 Teks berhasil terkirim ke {TELEGRAM_PUBLISH_CHANNEL}")
                    return True
                else:
                    error_desc: str = result.get("description", "Unknown error")
                    logger.error(f"❌ Gagal kirim teks: {error_desc}")
                    return False
    except Exception as e:
        logger.error(f"❌ Exception saat mengirim teks: {e}", exc_info=True)
        return False
