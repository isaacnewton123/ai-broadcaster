"""
main.py — Orchestrator utama Bot Broadcaster.

Berisi:
- Polling loop (cek MongoDB setiap POLL_INTERVAL_SECONDS)
- Queue & Throttle (jeda THROTTLE_DELAY_SECONDS antar posting)
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
    validate_gemini,
    validate_mongodb,
    validate_telegram,
)
from database import get_unposted_jobs, mark_as_posted
from poster_telegram import generate_portrait_bytes
from logger import get_logger
from telegram_publisher import send_photo_with_caption, send_text_only

logger = get_logger(__name__)

# ─── Type Aliases ─────────────────────────────────────────────────────────────

JobDocument = dict[str, Any]

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
    """Proses 1 loker: AI rewrite → render poster → kirim ke Telegram → catat.

    Args:
        job: Dokumen loker dari MongoDB.

    Returns:
        True jika seluruh proses berhasil, False jika gagal.
    """
    slug: str = job.get("slug", "unknown")
    company: str = job.get("company", "Perusahaan")
    logger.info(f"📋 Memproses: {company} [{slug}]")

    # Langkah 1: AI Social Rewrite
    logger.info("🤖 Memulai AI Social Rewrite...")
    caption: str = rewrite_for_social(job)
    logger.info(f"✅ Caption berhasil di-generate ({len(caption)} karakter)")

    # Langkah 2: Render Poster (in-memory)
    logger.info("🎨 Merender poster 1080x1350...")
    poster: io.BytesIO | None = generate_portrait_bytes(job)

    # Langkah 3: Kirim ke Telegram
    send_success: bool = False
    if poster is not None:
        logger.info("📤 Mengirim foto + caption ke Telegram...")
        send_success = await send_photo_with_caption(
            image_bytes=poster,
            caption=caption,
            filename=f"{slug}.png",
        )
        # Hapus poster dari memori
        poster.close()
    else:
        logger.warning("⚠️ Poster gagal dirender. Mengirim teks saja...")
        send_success = await send_text_only(caption)

    if not send_success:
        logger.error(f"❌ Gagal mengirim ke Telegram: {slug}")
        return False

    # Langkah 4: Catat ke broadcast_history
    recorded: bool = await mark_as_posted(slug)
    if not recorded:
        logger.error(f"⚠️ Terkirim ke Telegram, tapi gagal dicatat di history: {slug}")

    return True


# ─── Polling Loop ─────────────────────────────────────────────────────────────


async def polling_loop() -> None:
    """Loop utama: cek MongoDB → proses loker baru → tidur → ulangi."""
    logger.info("=" * 60)
    logger.info("🚀 Bot Broadcaster dimulai!")
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
    validate_telegram()
    validate_mongodb()
    validate_gemini()

    # Jalankan health check server dan polling loop secara paralel
    await asyncio.gather(
        start_health_server(),
        polling_loop(),
    )


if __name__ == "__main__":
    asyncio.run(main())
