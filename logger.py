"""
logger.py — Logging terpusat untuk Bot Broadcaster.

Output ke console (stdout) saja — Render.com free tier otomatis menangkap stdout.
Tidak menulis file log ke disk untuk menghemat storage.

Semua modul cukup: `from logger import get_logger`
"""

from __future__ import annotations

import logging
import sys

# ─── Konfigurasi ──────────────────────────────────────────────────────────────

_LOG_FORMAT: str = "%(asctime)s | %(name)-25s | %(levelname)-8s | %(message)s"
_LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"

_root_configured: bool = False


def _setup_root_logger() -> None:
    """Konfigurasi root logger sekali saja — hanya ke console."""
    global _root_configured
    if _root_configured:
        return

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # Console handler saja (stdout)
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_LOG_DATE_FORMAT))
    root.addHandler(console)

    _root_configured = True


def get_logger(name: str) -> logging.Logger:
    """
    Dapatkan logger dengan nama tertentu.

    Contoh:
        from logger import get_logger
        logger = get_logger(__name__)
        logger.info("Proses dimulai")
        logger.error("Ada kesalahan", exc_info=True)
    """
    _setup_root_logger()
    return logging.getLogger(name)
