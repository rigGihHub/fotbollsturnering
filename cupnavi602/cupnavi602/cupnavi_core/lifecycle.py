"""Turneringslivscykel och permanenta publika identifierare.

Interna värden är språk- och sportneutrala. UI:t ansvarar för översättning.
"""

from __future__ import annotations

import re
import unicodedata

LIFECYCLE_STATUSES = ("draft", "published", "live", "completed", "trashed")
PUBLIC_STATUSES = ("published", "live", "completed")
EDITABLE_STATUSES = ("draft", "published", "live")

STATUS_LABELS_SV = {
    "draft": "Utkast",
    "published": "Publicerad",
    "live": "Pågår",
    "completed": "Avslutad",
    "trashed": "Papperskorg",
}

STATUS_LABELS_EN = {
    "draft": "Draft",
    "published": "Published",
    "live": "Live",
    "completed": "Completed",
    "trashed": "Trash",
}


def normalize_status(value: str | None, *, is_published: bool = False) -> str:
    status = (value or "").strip().lower()
    if status in LIFECYCLE_STATUSES:
        return status
    return "published" if is_published else "draft"


def status_label(status: str | None, language: str = "sv") -> str:
    normalized = normalize_status(status)
    labels = STATUS_LABELS_EN if str(language).lower().startswith("en") else STATUS_LABELS_SV
    return labels[normalized]


def is_public_status(status: str | None) -> bool:
    return normalize_status(status) in PUBLIC_STATUSES


def is_editable_status(status: str | None) -> bool:
    return normalize_status(status) in EDITABLE_STATUSES


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    ascii_text = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    return ascii_text or "cup"


def slug_base(name: str, start_date: str | None = None) -> str:
    base = slugify(name)
    year = ""
    if start_date:
        match = re.match(r"^(\d{4})", str(start_date))
        if match:
            year = match.group(1)
    return f"{base}-{year}" if year else base


def choose_unique_slug(name: str, start_date: str | None, tournament_id: int, used_slugs) -> str:
    used = {str(item) for item in used_slugs if item}
    base = slug_base(name, start_date)
    if base not in used:
        return base
    candidate = f"{base}-{int(tournament_id)}"
    counter = 2
    while candidate in used:
        candidate = f"{base}-{int(tournament_id)}-{counter}"
        counter += 1
    return candidate
