"""Safe error diagnostics. Never stores exception tracebacks or personal form data."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib

def error_id(exc: Exception, context: str = "") -> str:
    raw = f"{type(exc).__name__}|{context}|{str(exc)[:120]}"
    return "CN-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:6].upper()

def safe_error_record(exc: Exception, *, context: str, app_version: str,
                      tournament_id: int | None = None) -> dict:
    return {
        "error_id": error_id(exc, context),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "app_version": str(app_version),
        "tournament_id": tournament_id,
        "context": str(context)[:100],
        "error_type": type(exc).__name__[:100],
        "message": str(exc)[:500],
    }

def persist_error(con, record: dict) -> None:
    con.execute(
        """INSERT INTO app_errors(error_id,created_at,app_version,tournament_id,context,error_type,message)
           VALUES(?,?,?,?,?,?,?)""",
        (record["error_id"], record["created_at"], record["app_version"], record["tournament_id"],
         record["context"], record["error_type"], record["message"]),
    )
