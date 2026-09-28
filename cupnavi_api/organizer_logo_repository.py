"""Small, durable organizer crests. Images are public; writes require cup access."""
from __future__ import annotations

import base64
import hashlib

from .repository import connect, one

MAX_IMAGE_BYTES = 500_000


def _content_type(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    raise ValueError("Välj en PNG-, JPG- eller WebP-bild")


def save_organizer_logo(tournament_id: int, encoded: str) -> str:
    if len(encoded) > (MAX_IMAGE_BYTES * 4 // 3 + 8):
        raise ValueError("Bilden får vara högst 500 kB")
    try:
        data = base64.b64decode(encoded, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise ValueError("Bilden kunde inte läsas") from exc
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise ValueError("Bilden får vara högst 500 kB")
    content_type = _content_type(data)
    digest = hashlib.sha256(data).hexdigest()
    with connect() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS organizer_logo_assets (
            digest TEXT PRIMARY KEY, tournament_id INTEGER NOT NULL,
            content_type TEXT NOT NULL, image_base64 TEXT NOT NULL
        )""")
        con.execute("INSERT OR IGNORE INTO organizer_logo_assets(digest,tournament_id,content_type,image_base64) VALUES(?,?,?,?)",
                    (digest,int(tournament_id),content_type,encoded))
        con.commit()
    return digest


def get_organizer_logo(digest: str):
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        return None
    try:
        row = one("SELECT content_type,image_base64 FROM organizer_logo_assets WHERE digest=?", (digest,))
    except Exception as exc:
        if "no such table: organizer_logo_assets" in str(exc).lower():
            return None
        raise
    if not row:
        return None
    return row["content_type"],base64.b64decode(row["image_base64"])
