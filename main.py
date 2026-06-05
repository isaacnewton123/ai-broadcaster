"""
main.py — Orchestrator utama Bot Broadcaster.

Berisi:
- Polling loop (cek MongoDB setiap POLL_INTERVAL_SECONDS)
- Queue & Throttle (jeda THROTTLE_DELAY_SECONDS antar posting)
- Multi-platform publishing: Telegram, Facebook, Instagram
- Health check server (/ping endpoint untuk Render uptime)

Cara pakai:
    python main.py
"""

from __future__ import annotations

import asyncio
import io
from typing import Any

from aiohttp import web

from ai_social_rewriter import rewrite_for_social
from config import (
    POLL_INTERVAL_SECONDS,
    PORT,
    THROTTLE_DELAY_SECONDS,
    validate_facebook,
    validate_gemini,
    validate_instagram,
    validate_mongodb,
    validate_telegram,
)
from database import get_unposted_jobs, mark_as_posted
from facebook_publisher import publish_photo_to_facebook, publish_text_to_facebook
from instagram_publisher import publish_photo_to_instagram
from poster_facebook import generate_landscape_bytes
from poster_instagram import generate_square_bytes
from poster_telegram import generate_portrait_bytes
from logger import get_logger
from telegram_publisher import send_photo_with_caption, send_text_only

logger = get_logger(__name__)

# ─── Type Aliases ─────────────────────────────────────────────────────────────

JobDocument = dict[str, Any]

# ─── Platform Flags ──────────────────────────────────────────────────────────

_fb_enabled: bool = False
_ig_enabled: bool = False

from server_stats import handle_root, handle_ping

async def start_health_server() -> None:
    """Jalankan web server kecil untuk health check / ping."""
    app = web.Application()
    app.router.add_get("/", handle_root)
    app.router.add_get("/ping", handle_ping)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"🌐 Health check server berjalan di port {PORT}")


# ─── Proses 1 Loker ──────────────────────────────────────────────────────────


async def process_single_job(job: JobDocument) -> bool:
    """Proses 1 loker: AI rewrite → render poster → kirim ke semua platform → catat.

    Args:
        job: Dokumen loker dari MongoDB.

    Returns:
        True jika minimal satu platform berhasil, False jika semua gagal.
    """
    slug: str = job.get("slug", "unknown")
    company: str = job.get("company", "Perusahaan")
    logger.info(f"📋 Memproses: {company} [{slug}]")

    # Langkah 1: AI Social Rewrite
    logger.info("🤖 Memulai AI Social Rewrite...")
    caption: str = rewrite_for_social(job)
    logger.info(f"✅ Caption berhasil di-generate ({len(caption)} karakter)")

    any_success: bool = False

    # ═══════════════════════════════════════════════════════════════════════
    # PLATFORM 1: TELEGRAM
    # ═══════════════════════════════════════════════════════════════════════
    logger.info("── 📱 Platform: TELEGRAM ──")
    tg_poster: io.BytesIO | None = generate_portrait_bytes(job)

    if tg_poster is not None:
        logger.info("📤 Mengirim foto + caption ke Telegram...")
        tg_success: bool = await send_photo_with_caption(
            image_bytes=tg_poster,
            caption=caption,
            filename=f"{slug}.png",
        )
        tg_poster.close()
        if tg_success:
            any_success = True
        else:
            logger.error("❌ Gagal mengirim ke Telegram.")
    else:
        logger.warning("⚠️ Poster Telegram gagal dirender. Mengirim teks saja...")
        tg_success = await send_text_only(caption)
        if tg_success:
            any_success = True

    # ═══════════════════════════════════════════════════════════════════════
    # PLATFORM 2: FACEBOOK
    # ═══════════════════════════════════════════════════════════════════════
    if _fb_enabled:
        logger.info("── 📘 Platform: FACEBOOK ──")
        fb_poster: io.BytesIO | None = generate_landscape_bytes(job)

        if fb_poster is not None:
            logger.info("📤 Mengirim foto + caption ke Facebook Page...")
            fb_success: bool = await publish_photo_to_facebook(
                image_bytes=fb_poster,
                caption=caption,
                filename=f"{slug}-fb.png",
            )
            fb_poster.close()
            if fb_success:
                any_success = True
            else:
                logger.error("❌ Gagal posting ke Facebook.")
        else:
            logger.warning("⚠️ Poster Facebook gagal dirender. Mengirim teks saja...")
            fb_success = await publish_text_to_facebook(caption)
            if fb_success:
                any_success = True

    # ═══════════════════════════════════════════════════════════════════════
    # PLATFORM 3: INSTAGRAM
    # ═══════════════════════════════════════════════════════════════════════
    if _ig_enabled:
        logger.info("── 📸 Platform: INSTAGRAM ──")
        ig_poster: io.BytesIO | None = generate_square_bytes(job)

        if ig_poster is not None:
            logger.info("📤 Mengirim foto + caption ke Instagram...")
            ig_success: bool = await publish_photo_to_instagram(
                image_bytes=ig_poster,
                caption=caption,
                slug=slug,
            )
            ig_poster.close()
            if ig_success:
                any_success = True
            else:
                logger.error("❌ Gagal posting ke Instagram.")
        else:
            logger.warning("⚠️ Poster Instagram gagal dirender. IG dilewati.")

    # ═══════════════════════════════════════════════════════════════════════

    if not any_success:
        logger.error(f"❌ Semua platform gagal untuk: {slug}")
        return False

    # Catat ke broadcast_history
    recorded: bool = await mark_as_posted(slug)
    if not recorded:
        logger.error(f"⚠️ Terkirim, tapi gagal dicatat di history: {slug}")

    return True


# ─── Polling Loop ─────────────────────────────────────────────────────────────


async def polling_loop() -> None:
    """Loop utama: cek MongoDB → proses loker baru → tidur → ulangi."""
    platforms: list[str] = ["Telegram"]
    if _fb_enabled:
        platforms.append("Facebook")
    if _ig_enabled:
        platforms.append("Instagram")

    logger.info("=" * 60)
    logger.info("🚀 Bot Broadcaster dimulai!")
    logger.info(f"📡 Platform aktif: {', '.join(platforms)}")
    logger.info(f"⏱  Interval polling: {POLL_INTERVAL_SECONDS} detik")
    logger.info(f"⏱  Jeda antar posting: {THROTTLE_DELAY_SECONDS} detik")
    logger.info("=" * 60)

    while True:
        try:
            # Ambil loker yang belum diposting
            unposted: list[JobDocument] = await get_unposted_jobs()

            if not unposted:
                logger.info("😴 Tidak ada loker baru. Tidur sejenak...")
            else:
                logger.info(f"📬 Ditemukan {len(unposted)} loker baru! Memulai antrean...")

                for index, job in enumerate(unposted, start=1):
                    slug: str = job.get("slug", "unknown")
                    logger.info(f"── Antrean [{index}/{len(unposted)}]: {slug}")

                    success: bool = await process_single_job(job)

                    if success and index < len(unposted):
                        logger.info(f"⏸  Jeda {THROTTLE_DELAY_SECONDS} detik (anti-spam)...")
                        await asyncio.sleep(THROTTLE_DELAY_SECONDS)

                logger.info("✅ Semua antrean selesai diproses!")

        except Exception as e:
            logger.error(f"💥 Error di polling loop: {e}", exc_info=True)

        logger.info(f"💤 Tidur {POLL_INTERVAL_SECONDS} detik sebelum cek lagi...")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


# ─── Entry Point ──────────────────────────────────────────────────────────────


async def main() -> None:
    """Entry point utama — validasi → server → polling."""
    global _fb_enabled, _ig_enabled

    validate_telegram()
    validate_mongodb()
    validate_gemini()
    _fb_enabled = validate_facebook()
    _ig_enabled = validate_instagram()

    # Jalankan health check server dan polling loop secara paralel
    await asyncio.gather(
        start_health_server(),
        polling_loop(),
    )


if __name__ == "__main__":
    asyncio.run(main())
