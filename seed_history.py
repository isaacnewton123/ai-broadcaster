"""
seed_history.py — Script seeding data lawas ke broadcast_history.

Dijalankan SATU KALI SAJA sebelum deployment pertama Bot Broadcaster.
Tugasnya: menyedot semua slug loker lawas dari koleksi `jobs` dan
memasukkannya ke `broadcast_history` agar bot tidak mem-posting
ratusan loker kedaluwarsa saat pertama kali dinyalakan.

Cara pakai:
    python seed_history.py
"""

from __future__ import annotations

import asyncio

from config import validate_mongodb
from database import seed_all_existing
from logger import get_logger

logger = get_logger(__name__)


async def main() -> None:
    """Entry point untuk seeding."""
    print("=" * 60)
    print("🌱 SEEDING: Memasukkan semua loker lawas ke broadcast_history")
    print("=" * 60)

    validate_mongodb()

    count: int = await seed_all_existing()

    print("=" * 60)
    if count > 0:
        print(f"✅ Selesai! {count} slug loker lawas berhasil di-seed.")
    else:
        print("ℹ️  Tidak ada slug baru untuk di-seed (semua sudah ada).")
    print("=" * 60)
    print("Bot Broadcaster sekarang aman untuk dinyalakan!")


if __name__ == "__main__":
    asyncio.run(main())
