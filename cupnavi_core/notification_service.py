"""Verified team-follow notification subscriptions.

Web push is intentionally not faked here. Delivery currently uses the existing
configurable SMTP transport; the data model is channel-ready for a future PWA.
"""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib, secrets

def new_token() -> str:
    return secrets.token_urlsafe(32)

def token_hash(token: str) -> str:
    return hashlib.sha256(str(token).encode("utf-8")).hexdigest()

def normalize_email(value: str) -> str:
    return str(value or "").strip().lower()

def category_enabled(subscription, category: str) -> bool:
    mapping={
        "schedule":"notify_schedule",
        "results":"notify_results",
        "messages":"notify_messages",
        "general":"notify_messages",
    }
    field=mapping.get(category,"notify_messages")
    try:
        return bool(subscription[field])
    except Exception:
        return bool(subscription.get(field,1))

def classify_notification(title: str) -> str:
    text=str(title or "").casefold()
    if any(word in text for word in ("resultat","slut:","mål")):
        return "results"
    if any(word in text for word in ("flytt","matchtid","försen","plan")):
        return "schedule"
    return "messages"

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
