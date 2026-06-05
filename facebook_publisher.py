"""
facebook_publisher.py — Pengirim postingan ke Facebook Page via Graph API.

Berisi:
- publish_photo_to_facebook()  : Upload foto + caption ke Fanspage
- publish_text_to_facebook()   : Posting teks saja (fallback)

Menggunakan aiohttp agar non-blocking dan kompatibel dengan asyncio.
"""

from __future__ import annotations

import io
from typing import Any, Optional

import aiohttp

from config import FB_PAGE_ACCESS_TOKEN, FB_PAGE_ID
from logger import get_logger

logger = get_logger(__name__)

# ─── Facebook Graph API Base URL ─────────────────────────────────────────────

_GRAPH_API_VERSION: str = "v19.0"
_BASE_URL: str = f"https://graph.facebook.com/{_GRAPH_API_VERSION}"


# ─── Kirim Foto + Caption ke Facebook Page ──────────────────────────────────


async def publish_photo_to_facebook(
    image_bytes: io.BytesIO,
    caption: str,
    filename: str = "poster.png",
) -> bool:
    """Upload foto + caption ke Facebook Page.

    Args:
        image_bytes: Gambar dalam bentuk BytesIO (di memori).
        caption: Teks caption / pesan yang menyertai gambar.
        filename: Nama file gambar (metadata saja).

    Returns:
        True jika berhasil terposting, False jika gagal.
    """
    if not FB_PAGE_ID or not FB_PAGE_ACCESS_TOKEN:
        logger.warning("Facebook belum dikonfigurasi. Melewati posting FB.")
        return False

    url: str = f"{_BASE_URL}/{FB_PAGE_ID}/photos"

    # Reset posisi baca BytesIO ke awal
    image_bytes.seek(0)

    data = aiohttp.FormData()
    data.add_field("access_token", FB_PAGE_ACCESS_TOKEN)
    data.add_field("message", caption[:63206])  # FB limit: 63.206 karakter
    data.add_field(
        "source",
        image_bytes,
        filename=filename,
        content_type="image/png",
    )

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                result: dict[str, Any] = await resp.json()

                if "id" in result:
                    post_id: str = result["id"]
                    logger.info(f"📘 Foto berhasil terposting ke Facebook Page! Post ID: {post_id}")
                    return True
                else:
                    error_msg: str = result.get("error", {}).get("message", "Unknown error")
                    error_code: int = result.get("error", {}).get("code", 0)
                    logger.error(f"❌ Gagal posting ke Facebook: [{error_code}] {error_msg}")
                    return False

    except Exception as e:
        logger.error(f"❌ Exception saat posting ke Facebook: {e}", exc_info=True)
        return False


# ─── Kirim Teks Saja ke Facebook Page (Fallback) ────────────────────────────


async def publish_text_to_facebook(caption: str) -> bool:
    """Posting teks saja ke Facebook Page (fallback jika poster gagal).

    Args:
        caption: Teks pesan yang akan diposting.

    Returns:
        True jika berhasil terposting, False jika gagal.
    """
    if not FB_PAGE_ID or not FB_PAGE_ACCESS_TOKEN:
        logger.warning("Facebook belum dikonfigurasi. Melewati posting FB.")
        return False

    url: str = f"{_BASE_URL}/{FB_PAGE_ID}/feed"

    payload: dict[str, str] = {
        "access_token": FB_PAGE_ACCESS_TOKEN,
        "message": caption[:63206],
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                result: dict[str, Any] = await resp.json()

                if "id" in result:
                    post_id: str = result["id"]
                    logger.info(f"📘 Teks berhasil terposting ke Facebook Page! Post ID: {post_id}")
                    return True
                else:
                    error_msg: str = result.get("error", {}).get("message", "Unknown error")
                    logger.error(f"❌ Gagal posting teks ke Facebook: {error_msg}")
                    return False

    except Exception as e:
        logger.error(f"❌ Exception saat posting teks ke Facebook: {e}", exc_info=True)
        return False
