"""
instagram_publisher.py — Pengirim postingan ke Instagram Business via Graph API.

Berisi:
- publish_photo_to_instagram()  : Posting foto + caption ke Instagram Feed

Flow Instagram Graph API (2 langkah):
1. Buat "media container" — kirim URL gambar + caption
2. Publish container — jadikan postingan resmi

CATATAN PENTING:
Instagram Graph API TIDAK menerima upload file langsung (berbeda dari Facebook).
Gambar harus berupa URL publik yang bisa diakses oleh server Facebook/Instagram.
Kita menggunakan Cloudflare R2 sebagai penyimpanan sementara.
"""

from __future__ import annotations

import asyncio
import io
from typing import Any, Optional

import aiohttp

from config import FB_PAGE_ACCESS_TOKEN, IG_ACCOUNT_ID
from logger import get_logger
from r2_uploader import upload_poster_to_r2

logger = get_logger(__name__)

# ─── Instagram Graph API Base URL ────────────────────────────────────────────

_GRAPH_API_VERSION: str = "v19.0"
_BASE_URL: str = f"https://graph.facebook.com/{_GRAPH_API_VERSION}"


# ─── Kirim Foto + Caption ke Instagram ──────────────────────────────────────


async def publish_photo_to_instagram(
    image_bytes: io.BytesIO,
    caption: str,
    slug: str = "poster",
) -> bool:
    """Posting foto + caption ke Instagram Business.

    Flow:
    1. Upload gambar ke Cloudflare R2 (agar punya URL publik)
    2. Buat media container di Instagram API
    3. Tunggu container selesai diproses
    4. Publish container

    Args:
        image_bytes: Gambar poster dalam bentuk BytesIO (in-memory).
        caption: Teks caption untuk postingan Instagram.
        slug: Slug loker untuk penamaan file di R2.

    Returns:
        True jika berhasil terposting, False jika gagal.
    """
    if not IG_ACCOUNT_ID or not FB_PAGE_ACCESS_TOKEN:
        logger.warning("Instagram belum dikonfigurasi. Melewati posting IG.")
        return False

    # ─── Step 1: Upload ke R2 ─────────────────────────────────────────────
    logger.info("📸 Mengupload poster IG ke R2...")
    r2_filename: str = f"poster-ig-{slug}.png"
    image_url: Optional[str] = upload_poster_to_r2(image_bytes, r2_filename)

    if not image_url:
        logger.error("❌ Gagal upload poster IG ke R2. Posting IG dibatalkan.")
        return False

    logger.info(f"✅ Poster IG tersedia di: {image_url}")

    try:
        async with aiohttp.ClientSession() as session:
            # ─── Step 2: Buat Media Container ─────────────────────────────
            container_url: str = f"{_BASE_URL}/{IG_ACCOUNT_ID}/media"
            container_params: dict[str, str] = {
                "image_url": image_url,
                "caption": caption[:2200],  # IG limit: 2.200 karakter
                "access_token": FB_PAGE_ACCESS_TOKEN,
            }

            logger.info("📦 Membuat media container di Instagram...")
            async with session.post(
                container_url, data=container_params,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                result: dict[str, Any] = await resp.json()

                if "id" not in result:
                    error_msg: str = result.get("error", {}).get("message", "Unknown error")
                    error_code: int = result.get("error", {}).get("code", 0)
                    logger.error(
                        f"❌ Gagal membuat container IG: [{error_code}] {error_msg}"
                    )
                    return False

                container_id: str = result["id"]
                logger.info(f"📦 Container ID: {container_id}")

            # ─── Step 3: Tunggu Container Siap ───────────────────────────
            # Instagram butuh waktu untuk memproses gambar
            status_url: str = f"{_BASE_URL}/{container_id}"
            status_params: dict[str, str] = {
                "fields": "status_code",
                "access_token": FB_PAGE_ACCESS_TOKEN,
            }

            max_retries: int = 10
            for attempt in range(1, max_retries + 1):
                await asyncio.sleep(3)  # Tunggu 3 detik setiap cek
                async with session.get(
                    status_url, params=status_params,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as status_resp:
                    status_data: dict[str, Any] = await status_resp.json()
                    status_code: str = status_data.get("status_code", "UNKNOWN")
                    logger.info(f"   ⏳ Container status [{attempt}/{max_retries}]: {status_code}")

                    if status_code == "FINISHED":
                        break
                    elif status_code == "ERROR":
                        logger.error("❌ Container IG mengalami error saat diproses.")
                        return False
            else:
                logger.error("❌ Timeout: Container IG tidak siap setelah 30 detik.")
                return False

            # ─── Step 4: Publish! ─────────────────────────────────────────
            publish_url: str = f"{_BASE_URL}/{IG_ACCOUNT_ID}/media_publish"
            publish_params: dict[str, str] = {
                "creation_id": container_id,
                "access_token": FB_PAGE_ACCESS_TOKEN,
            }

            logger.info("🚀 Mempublikasikan ke Instagram Feed...")
            async with session.post(
                publish_url, data=publish_params,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as pub_resp:
                pub_result: dict[str, Any] = await pub_resp.json()

                if "id" in pub_result:
                    media_id: str = pub_result["id"]
                    logger.info(f"📸 Foto berhasil terposting ke Instagram! Media ID: {media_id}")
                    return True
                else:
                    error_msg = pub_result.get("error", {}).get("message", "Unknown error")
                    logger.error(f"❌ Gagal publish ke Instagram: {error_msg}")
                    return False

    except Exception as e:
        logger.error(f"❌ Exception saat posting ke Instagram: {e}", exc_info=True)
        return False
