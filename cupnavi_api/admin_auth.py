"""Server-side organizer authentication for the Next/FastAPI admin."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time

SESSION_TTL_SECONDS = 60 * 60 * 12


def normalize_email(value: str) -> str:
    return str(value or "").strip().casefold()


def password_hash(password: str, salt_hex: str) -> str:
    """Match the scrypt parameters used by the Streamlit organizer accounts."""
    return hashlib.scrypt(
        str(password).encode("utf-8"),
        salt=bytes.fromhex(str(salt_hex)),
        n=2**14,
        r=8,
        p=1,
        dklen=32,
    ).hex()


def _session_secret() -> bytes:
    # CUPNAVI_SESSION_SECRET is preferred. TURSO_AUTH_TOKEN keeps existing
    # deployments functional until a dedicated session secret is configured.
    secret = (
        os.getenv("CUPNAVI_SESSION_SECRET")
        or os.getenv("TURSO_AUTH_TOKEN")
        or os.getenv("ADMIN_PASSWORD")
        or ""
    )
    if not secret:
        raise RuntimeError("CupNavi admin sessions are not configured")
    return hashlib.sha256(("cupnavi-admin-session\0" + secret).encode("utf-8")).digest()


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def issue_session(account: dict) -> str:
    now = int(time.time())
    payload = {
        "sub": int(account["id"]),
        "email": normalize_email(account["email"]),
        "iat": now,
        "exp": now + SESSION_TTL_SECONDS,
    }
    body = _b64encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signature = _b64encode(hmac.new(_session_secret(), body.encode("ascii"), hashlib.sha256).digest())
    return f"{body}.{signature}"


def verify_session(token: str) -> dict | None:
    try:
        body, supplied_signature = str(token or "").split(".", 1)
        expected_signature = _b64encode(
            hmac.new(_session_secret(), body.encode("ascii"), hashlib.sha256).digest()
        )
        if not hmac.compare_digest(supplied_signature, expected_signature):
            return None
        payload = json.loads(_b64decode(body).decode("utf-8"))
        if int(payload.get("exp") or 0) <= int(time.time()):
            return None
        account_id = int(payload.get("sub") or 0)
        if account_id <= 0:
            return None
        return payload
    except (ValueError, TypeError, json.JSONDecodeError, RuntimeError):
        return None
