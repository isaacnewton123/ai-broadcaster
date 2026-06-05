"""
r2_uploader.py — Upload gambar poster ke Cloudflare R2.

Dibutuhkan oleh Instagram Graph API yang mengharuskan gambar berupa URL publik.
Flow: BytesIO → Upload ke R2 → Return URL publik (cdn.nyarikerja.online/...).

Menggunakan urllib + HMAC (AWS Signature V4) agar tidak butuh package boto3.
"""

from __future__ import annotations

import hashlib
import hmac
import io
import time
import urllib.request
from datetime import datetime, timezone
from typing import Optional

from config import (
    R2_ACCESS_KEY_ID,
    R2_ACCOUNT_ID,
    R2_BUCKET_NAME,
    R2_PUBLIC_DOMAIN,
    R2_SECRET_ACCESS_KEY,
)
from logger import get_logger

logger = get_logger(__name__)


# ─── AWS Signature V4 Helpers ────────────────────────────────────────────────


def _sign(key: bytes, msg: str) -> bytes:
    """HMAC-SHA256 signing helper."""
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _get_signature_key(secret: str, date_stamp: str, region: str, service: str) -> bytes:
    """Derive the signing key for AWS Signature V4."""
    k_date = _sign(("AWS4" + secret).encode("utf-8"), date_stamp)
    k_region = _sign(k_date, region)
    k_service = _sign(k_region, service)
    k_signing = _sign(k_service, "aws4_request")
    return k_signing


# ─── Upload Poster ke R2 ────────────────────────────────────────────────────


def upload_poster_to_r2(image_bytes: io.BytesIO, filename: str) -> Optional[str]:
    """Upload gambar poster ke Cloudflare R2 dan kembalikan URL publiknya.

    Args:
        image_bytes: Gambar dalam bentuk BytesIO (in-memory).
        filename: Nama file tujuan di R2 (misal: poster-ig-slug.png).

    Returns:
        URL publik gambar (misal: https://cdn.nyarikerja.online/poster-ig-slug.png),
        atau None jika gagal.
    """
    if not R2_ACCESS_KEY_ID or not R2_SECRET_ACCESS_KEY or not R2_ACCOUNT_ID:
        logger.error("R2 credentials belum dikonfigurasi. Tidak bisa upload.")
        return None

    try:
        image_bytes.seek(0)
        body: bytes = image_bytes.read()

        # R2 endpoint
        host: str = f"{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
        endpoint: str = f"https://{host}/{R2_BUCKET_NAME}/{filename}"

        # Timestamps
        now = datetime.now(timezone.utc)
        amz_date: str = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp: str = now.strftime("%Y%m%d")

        # Content hash
        payload_hash: str = hashlib.sha256(body).hexdigest()

        # Canonical request
        method: str = "PUT"
        canonical_uri: str = f"/{R2_BUCKET_NAME}/{filename}"
        canonical_querystring: str = ""
        content_type: str = "image/png"

        canonical_headers: str = (
            f"content-type:{content_type}\n"
            f"host:{host}\n"
            f"x-amz-content-sha256:{payload_hash}\n"
            f"x-amz-date:{amz_date}\n"
        )
        signed_headers: str = "content-type;host;x-amz-content-sha256;x-amz-date"

        canonical_request: str = (
            f"{method}\n"
            f"{canonical_uri}\n"
            f"{canonical_querystring}\n"
            f"{canonical_headers}\n"
            f"{signed_headers}\n"
            f"{payload_hash}"
        )

        # String to sign
        region: str = "auto"
        service: str = "s3"
        credential_scope: str = f"{date_stamp}/{region}/{service}/aws4_request"
        string_to_sign: str = (
            f"AWS4-HMAC-SHA256\n"
            f"{amz_date}\n"
            f"{credential_scope}\n"
            f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
        )

        # Signing key & signature
        signing_key: bytes = _get_signature_key(R2_SECRET_ACCESS_KEY, date_stamp, region, service)
        signature: str = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

        # Authorization header
        authorization: str = (
            f"AWS4-HMAC-SHA256 "
            f"Credential={R2_ACCESS_KEY_ID}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )

        headers: dict[str, str] = {
            "Content-Type": content_type,
            "x-amz-content-sha256": payload_hash,
            "x-amz-date": amz_date,
            "Authorization": authorization,
        }

        req = urllib.request.Request(endpoint, data=body, headers=headers, method="PUT")

        with urllib.request.urlopen(req, timeout=30) as response:
            if response.status in (200, 201):
                public_url: str = f"{R2_PUBLIC_DOMAIN}/{filename}"
                logger.info(f"✅ Upload R2 berhasil: {public_url}")
                return public_url
            else:
                logger.error(f"❌ Upload R2 gagal: HTTP {response.status}")
                return None

    except Exception as e:
        error_detail: str = ""
        if hasattr(e, "read"):
            error_detail = e.read().decode("utf-8", errors="ignore")
        logger.error(f"❌ Exception saat upload ke R2: {e} | Detail: {error_detail}")
        return None
