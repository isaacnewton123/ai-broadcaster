"""
ai_social_rewriter.py — Universal Caption Generator untuk sosial media.

Berisi:
- rewrite_for_social()  : Kirim data loker ke Gemini, terima caption sosmed universal

Satu kali rewrite, hasilnya kompatibel di Telegram, Instagram, dan Facebook.
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any, Optional

from config import GEMINI_API_KEY, GEMINI_MODELS
from logger import get_logger

logger = get_logger(__name__)

# ─── Type Aliases ─────────────────────────────────────────────────────────────

JobDocument = dict[str, Any]

# ─── Prompt Template ─────────────────────────────────────────────────────────

SOCIAL_PROMPT_TEMPLATE: str = (
    "Kamu adalah Social Media Manager profesional untuk portal lowongan kerja Indonesia bernama nyarikerja.online.\n"
    "Tugas kamu: buatkan SATU caption sosial media yang UNIVERSAL (bisa dipakai di Telegram, Instagram, dan Facebook sekaligus).\n\n"
    "DATA LOKER:\n"
    "- Perusahaan: {company}\n"
    "- Posisi: {positions}\n"
    "- Lokasi: {location}\n"
    "- Tipe: {job_type}\n"
    "- Pendidikan: {education}\n"
    "- Gaji: {salaries}\n"
    "- Link: {job_url}\n\n"
    "ATURAN:\n"
    "1. Caption HARUS singkat, padat, dan menarik (maksimal 600 karakter).\n"
    "2. WAJIB gunakan emoji yang relevan di setiap baris untuk mempercantik.\n"
    "3. Sorot informasi GAJI jika tersedia (orang Indonesia sangat tertarik dengan gaji).\n"
    "4. Sorot POSISI dan LOKASI agar mudah ditemukan.\n"
    "5. Akhiri dengan ajakan (Call to Action) yang kuat: 'Klik link di bawah untuk melamar!' atau sejenisnya.\n"
    "6. JANGAN gunakan hashtag (#). Cukup emoji dan teks saja.\n"
    "7. JANGAN gunakan markdown bold (**) atau italic (*). Gunakan plain text saja.\n"
    "8. FORMAT RESPONSE: Respon HANYA berupa JSON murni (tanpa markdown code block). Format:\n"
    '{{"caption": "isi caption di sini"}}\n'
)

# ─── Fallback Caption ────────────────────────────────────────────────────────

def _build_fallback_caption(job: JobDocument) -> str:
    """Buat caption fallback jika semua model AI gagal."""
    company: str = job.get("company", "Perusahaan")
    location: str = job.get("location", "Indonesia")
    slug: str = job.get("slug", "")
    job_url: str = f"https://www.nyarikerja.online/lowongan/{slug}"

    positions: list[str] = [j.get("position", "") for j in job.get("jobs", [])]
    positions_text: str = ", ".join(positions[:3]) if positions else "Berbagai Posisi"

    salaries: list[dict[str, str]] = job.get("salaries", [])
    salary_text: str = ""
    if salaries:
        salary_text = f"\n💰 Gaji: {salaries[0].get('salary', 'Kompetitif')}"

    return (
        f"🏢 {company}\n"
        f"📋 Posisi: {positions_text}\n"
        f"📍 Lokasi: {location}"
        f"{salary_text}\n\n"
        f"📩 Lamar sekarang di:\n"
        f"{job_url}"
    )


# ─── Helper: Ekstrak Data dari Dokumen ────────────────────────────────────────

def _extract_prompt_data(job: JobDocument) -> dict[str, str]:
    """Ekstrak field-field penting dari dokumen loker untuk prompt AI."""
    company: str = job.get("company", "Tidak diketahui")
    location: str = job.get("location", "Indonesia")
    job_type: str = job.get("job_type", "")
    education: str = job.get("education", "")
    slug: str = job.get("slug", "")
    job_url: str = f"https://www.nyarikerja.online/lowongan/{slug}"

    positions: list[str] = [j.get("position", "") for j in job.get("jobs", [])]
    positions_text: str = ", ".join(positions[:5]) if positions else "Berbagai Posisi"

    salaries: list[dict[str, str]] = job.get("salaries", [])
    salary_text: str = "Tidak disebutkan"
    if salaries:
        salary_parts: list[str] = [
            f"{s.get('position', '')}: {s.get('salary', '')}" for s in salaries[:3]
        ]
        salary_text = " | ".join(salary_parts)

    return {
        "company": company,
        "positions": positions_text,
        "location": location,
        "job_type": job_type or "Tidak disebutkan",
        "education": education or "Tidak disebutkan",
        "salaries": salary_text,
        "job_url": job_url,
    }


# ─── Main Function ───────────────────────────────────────────────────────────

def rewrite_for_social(job: JobDocument) -> str:
    """Kirim data loker ke Gemini AI dan terima caption sosmed universal.

    Mencoba beberapa model secara berurutan. Jika semua gagal,
    kembalikan fallback caption.

    Args:
        job: Dokumen loker lengkap dari MongoDB.

    Returns:
        String caption siap posting ke semua platform sosmed.
    """
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY tidak tersedia. Menggunakan fallback caption.")
        return _build_fallback_caption(job)

    prompt_data: dict[str, str] = _extract_prompt_data(job)
    prompt: str = SOCIAL_PROMPT_TEMPLATE.format(**prompt_data)

    headers: dict[str, str] = {"Content-Type": "application/json"}
    payload: bytes = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }).encode("utf-8")

    for model in GEMINI_MODELS:
        url: str = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={GEMINI_API_KEY}"
        )
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        try:
            logger.info(f"Mencoba AI model: {model}...")
            with urllib.request.urlopen(req, timeout=30) as response:
                result: dict[str, Any] = json.loads(response.read().decode())
                raw_ai: str = result["candidates"][0]["content"]["parts"][0]["text"]
                ai_json: dict[str, str] = json.loads(raw_ai)
                caption: str = ai_json.get("caption", "")
                if caption:
                    logger.info(f"✅ Caption berhasil di-generate oleh model: {model}")
                    return caption
                logger.warning(f"Model {model} mengembalikan caption kosong.")
        except Exception as e:
            logger.warning(f"Model {model} gagal: {e}")
            continue

    logger.error("Semua model AI gagal. Menggunakan fallback caption.")
    return _build_fallback_caption(job)
