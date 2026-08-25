"""Configurable SMTP notification delivery. Messages are persisted independently."""
from __future__ import annotations
import os, smtplib
from email.message import EmailMessage


def smtp_configured() -> bool:
    return bool(os.getenv("CUPNAVI_SMTP_HOST") and os.getenv("CUPNAVI_SMTP_FROM"))


def send_notification_email(recipient: str, subject: str, body: str) -> tuple[bool, str | None]:
    recipient = str(recipient or "").strip()
    if not recipient:
        return False, "recipient_missing"
    host = os.getenv("CUPNAVI_SMTP_HOST", "").strip()
    sender = os.getenv("CUPNAVI_SMTP_FROM", "").strip()
    if not host or not sender:
        return False, "smtp_not_configured"
    port = int(os.getenv("CUPNAVI_SMTP_PORT", "587"))
    username = os.getenv("CUPNAVI_SMTP_USERNAME", "").strip()
    password = os.getenv("CUPNAVI_SMTP_PASSWORD", "")
    use_tls = os.getenv("CUPNAVI_SMTP_TLS", "1").strip().lower() not in {"0","false","no"}
    msg = EmailMessage()
    msg["From"] = sender; msg["To"] = recipient; msg["Subject"] = subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(host, port, timeout=10) as smtp:
            if use_tls: smtp.starttls()
            if username: smtp.login(username, password)
            smtp.send_message(msg)
        return True, None
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"[:500]
