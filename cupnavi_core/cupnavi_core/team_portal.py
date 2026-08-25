"""Domänhjälpare för CupNavis deltagar-/lagportal."""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generate_access_code(length=6):
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(length))


def new_code_hash(code):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", code.strip().upper().encode(), bytes.fromhex(salt), 120_000).hex()
    return salt, digest


def verify_access_code(code, salt, expected_hash):
    if not code or not salt or not expected_hash:
        return False
    actual = hashlib.pbkdf2_hmac("sha256", code.strip().upper().encode(), bytes.fromhex(salt), 120_000).hex()
    return hmac.compare_digest(actual, expected_hash)


def squad_deadline_at(scheduled_start, deadline_minutes):
    if not scheduled_start:
        return None
    start = datetime.fromisoformat(str(scheduled_start))
    return start - timedelta(minutes=max(0, int(deadline_minutes or 0)))


def squad_is_locked(scheduled_start, deadline_minutes, now=None):
    deadline = squad_deadline_at(scheduled_start, deadline_minutes)
    if deadline is None:
        return False
    return (now or datetime.now()) >= deadline
