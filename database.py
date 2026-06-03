"""
database.py — Koneksi dan operasi MongoDB Atlas untuk Bot Broadcaster.

Berisi:
- get_unposted_jobs()  : Ambil loker dari koleksi `jobs` yang belum tercatat di `broadcast_history`
- mark_as_posted()     : Catat slug loker ke koleksi `broadcast_history`
- seed_all_existing()  : Masukkan semua slug yang sudah ada ke `broadcast_history` (seeding)

Menggunakan `motor` (async MongoDB driver) agar kompatibel dengan asyncio.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import motor.motor_asyncio

from config import (
    MONGODB_DB_NAME,
    MONGODB_HISTORY_COLLECTION,
    MONGODB_JOBS_COLLECTION,
    MONGODB_URI,
)
from logger import get_logger

logger = get_logger(__name__)

# ─── Type Aliases ─────────────────────────────────────────────────────────────

JobDocument = dict[str, Any]

# ─── MongoDB Client (Singleton) ──────────────────────────────────────────────

_client: motor.motor_asyncio.AsyncIOMotorClient | None = None


def _get_client() -> motor.motor_asyncio.AsyncIOMotorClient:
    """Mendapatkan atau membuat MongoDB client (singleton)."""
    global _client
    if _client is None:
        _client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI)
        logger.info("Koneksi MongoDB Atlas berhasil dibuat.")
    return _client


def _get_db() -> motor.motor_asyncio.AsyncIOMotorDatabase:
    """Mendapatkan referensi database."""
    return _get_client()[MONGODB_DB_NAME]


def _get_jobs_collection() -> motor.motor_asyncio.AsyncIOMotorCollection:
    """Mendapatkan referensi koleksi `jobs`."""
    return _get_db()[MONGODB_JOBS_COLLECTION]


def _get_history_collection() -> motor.motor_asyncio.AsyncIOMotorCollection:
    """Mendapatkan referensi koleksi `broadcast_history`."""
    return _get_db()[MONGODB_HISTORY_COLLECTION]


# ─── Query: Ambil Loker yang Belum Diposting ─────────────────────────────────

async def get_unposted_jobs() -> list[JobDocument]:
    """Ambil loker dari koleksi `jobs` yang slug-nya belum ada di `broadcast_history`.

    Returns:
        List berisi dokumen loker yang belum pernah di-broadcast.
    """
    history_col = _get_history_collection()
    jobs_col = _get_jobs_collection()

    # Ambil semua slug yang sudah pernah diposting
    posted_slugs: list[str] = await history_col.distinct("slug")
    logger.info(f"Total slug di broadcast_history: {len(posted_slugs)}")

    # Cari loker yang slug-nya belum ada di daftar posted
    query: dict[str, Any] = {"slug": {"$nin": posted_slugs}}
    cursor = jobs_col.find(query).sort("created_at", -1)

    unposted: list[JobDocument] = await cursor.to_list(length=100)
    logger.info(f"Ditemukan {len(unposted)} loker baru yang belum di-broadcast.")
    return unposted


# ─── Record: Catat Slug ke Broadcast History ─────────────────────────────────

async def mark_as_posted(slug: str) -> bool:
    """Catat slug loker yang sudah berhasil di-broadcast ke `broadcast_history`.

    Args:
        slug: Slug unik dari loker yang sudah terkirim ke Telegram.

    Returns:
        True jika berhasil dicatat, False jika gagal.
    """
    history_col = _get_history_collection()

    try:
        document: dict[str, str] = {
            "slug": slug,
            "posted_at": datetime.now(timezone.utc).isoformat(),
        }
        await history_col.insert_one(document)
        logger.info(f"✅ Tercatat di broadcast_history: {slug}")
        return True
    except Exception as e:
        logger.error(f"❌ Gagal mencatat ke broadcast_history: {e}", exc_info=True)
        return False


# ─── Seeding: Masukkan Semua Slug yang Sudah Ada ─────────────────────────────

async def seed_all_existing() -> int:
    """Masukkan semua slug dari koleksi `jobs` ke `broadcast_history`.

    Dijalankan SATU KALI saja sebelum deployment pertama.
    Slug yang sudah ada di history akan dilewati (tidak duplikat).

    Returns:
        Jumlah slug baru yang berhasil di-seed.
    """
    jobs_col = _get_jobs_collection()
    history_col = _get_history_collection()

    # Ambil semua slug dari jobs
    all_slugs: list[str] = await jobs_col.distinct("slug")
    logger.info(f"Total slug di koleksi jobs: {len(all_slugs)}")

    # Ambil slug yang sudah ada di history
    existing_slugs: set[str] = set(await history_col.distinct("slug"))
    logger.info(f"Slug yang sudah ada di history: {len(existing_slugs)}")

    # Filter hanya slug baru
    new_slugs: list[str] = [s for s in all_slugs if s and s not in existing_slugs]

    if not new_slugs:
        logger.info("Tidak ada slug baru untuk di-seed.")
        return 0

    # Masukkan secara massal
    now: str = datetime.now(timezone.utc).isoformat()
    documents: list[dict[str, str]] = [
        {"slug": slug, "posted_at": now}
        for slug in new_slugs
    ]

    result = await history_col.insert_many(documents)
    count: int = len(result.inserted_ids)
    logger.info(f"🌱 Seeding selesai: {count} slug baru berhasil dimasukkan.")
    return count
