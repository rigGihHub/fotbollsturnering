"""Server-side organizer authentication for the Next/FastAPI admin."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time

SESSION_TTL_SECONDS = 60 * 60 * 12
OWNER_ACCOUNT_ID = 0
OWNER_ROLE = "owner"


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


def authenticate_owner(email: str, password: str) -> dict | None:
    """Authenticate the environment-only creator credential.

    No fallback credential is allowed. Both variables must be configured on the
    server and are compared in constant time. The returned account is synthetic;
    no owner password or hash is persisted in CupNavi's database.
    """
    expected_email = normalize_email(os.getenv("CUPNAVI_OWNER_EMAIL") or "")
    expected_password = os.getenv("CUPNAVI_OWNER_PASSWORD") or ""
    supplied_email = normalize_email(email)
    supplied_password = str(password or "")
    if not expected_email or not expected_password:
        return None
    if not hmac.compare_digest(supplied_email, expected_email):
        return None
    if not hmac.compare_digest(supplied_password, expected_password):
        return None
    return {
        "id": OWNER_ACCOUNT_ID,
        "email": expected_email,
        "display_name": "CupNavi Owner",
        "role": OWNER_ROLE,
        "is_owner": True,
    }


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
    role = str(account.get("role") or "organizer")
    account_id = int(account.get("id") or 0)
    payload = {
        "sub": account_id,
        "email": normalize_email(account["email"]),
        "role": role,
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
        role = str(payload.get("role") or "organizer")
        account_id = int(payload.get("sub") or 0)
        if role == OWNER_ROLE:
            if account_id != OWNER_ACCOUNT_ID:
                return None
        elif account_id <= 0:
            return None
        return payload
    except (ValueError, TypeError, json.JSONDecodeError, RuntimeError):
        return None
