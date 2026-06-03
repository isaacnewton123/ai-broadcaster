"""
config.py — Konfigurasi terpusat untuk Bot Broadcaster.

Load .env sekali, validasi variabel wajib, dan export sebagai konstanta bertipe.
Semua modul lain cukup: `from config import TELEGRAM_BOT_TOKEN, MONGODB_URI, ...`
"""

from __future__ import annotations

import os
import sys
from typing import Optional

# ─── Load .env ────────────────────────────────────────────────────────────────

_ENV_PATH: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

if os.path.exists(_ENV_PATH):
    with open(_ENV_PATH, encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _key, _val = _line.split("=", 1)
                os.environ[_key.strip()] = _val.strip().strip("\"'")

# ─── Telegram Bot API ────────────────────────────────────────────────────────

TELEGRAM_BOT_TOKEN: Optional[str] = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_PUBLISH_CHANNEL: str = os.environ.get("TELEGRAM_PUBLISH_CHANNEL", "")

# ─── Gemini AI ────────────────────────────────────────────────────────────────

GEMINI_API_KEY: Optional[str] = os.environ.get("GEMINI_API_KEY")

GEMINI_MODELS: list[str] = [
    "gemini-3.5-flash",
    "gemini-3-flash",
    "gemini-2.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash-lite",
]

# ─── MongoDB ──────────────────────────────────────────────────────────────────

MONGODB_URI: Optional[str] = os.environ.get("MONGODB_URI")
MONGODB_DB_NAME: str = os.environ.get("MONGODB_DB_NAME", "nyarikerja_db")
MONGODB_JOBS_COLLECTION: str = os.environ.get("MONGODB_JOBS_COLLECTION", "jobs")
MONGODB_HISTORY_COLLECTION: str = os.environ.get("MONGODB_HISTORY_COLLECTION", "broadcast_history")

# ─── Polling ──────────────────────────────────────────────────────────────────

POLL_INTERVAL_SECONDS: int = int(os.environ.get("POLL_INTERVAL_SECONDS", "300"))
THROTTLE_DELAY_SECONDS: int = int(os.environ.get("THROTTLE_DELAY_SECONDS", "15"))

# ─── Server (Ping / Health Check) ────────────────────────────────────────────

PORT: int = int(os.environ.get("PORT", "10000"))

# ─── Validasi ─────────────────────────────────────────────────────────────────

def validate_telegram() -> None:
    """Pastikan TELEGRAM_BOT_TOKEN dan TELEGRAM_PUBLISH_CHANNEL sudah diset."""
    if not TELEGRAM_BOT_TOKEN:
        print("=" * 70)
        print("ERROR: TELEGRAM_BOT_TOKEN belum diset di .env")
        print("Dapatkan dari @BotFather di Telegram.")
        print("=" * 70)
        sys.exit(1)
    if not TELEGRAM_PUBLISH_CHANNEL:
        print("=" * 70)
        print("ERROR: TELEGRAM_PUBLISH_CHANNEL belum diset di .env")
        print("Isi dengan username channel Anda (misal: @nyarikerja_online)")
        print("=" * 70)
        sys.exit(1)


def validate_gemini() -> None:
    """Peringatan jika GEMINI_API_KEY belum diset."""
    if not GEMINI_API_KEY:
        print("PERINGATAN: GEMINI_API_KEY belum diset. AI rewriting akan dilewati.")


def validate_mongodb() -> None:
    """Pastikan MONGODB_URI sudah diset. Exit jika belum."""
    if not MONGODB_URI:
        print("=" * 70)
        print("ERROR: MONGODB_URI belum diset di .env")
        print("Isi dengan connection string MongoDB Atlas Anda.")
        print("=" * 70)
        sys.exit(1)
