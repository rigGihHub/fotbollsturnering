"""Portabel turneringsbackup i JSON-format."""

import hashlib
import json
from datetime import datetime, timezone

BACKUP_FORMAT_VERSION = 1


def build_backup_bytes(app_version, tournament_id, datasets):
    payload = {
        "format": "cupnavi-tournament-backup",
        "format_version": BACKUP_FORMAT_VERSION,
        "app_version": app_version,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tournament_id": int(tournament_id),
        "data": datasets,
    }
    body = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        default=str,
    ).encode("utf-8")
    checksum = hashlib.sha256(body).hexdigest()
    return body, checksum


def validate_backup_bytes(data):
    payload = json.loads(data.decode("utf-8"))
    if payload.get("format") != "cupnavi-tournament-backup":
        raise ValueError("Fel backupformat.")
    if payload.get("format_version") != BACKUP_FORMAT_VERSION:
        raise ValueError("Backupversionen stöds inte.")
    if not isinstance(payload.get("data"), dict):
        raise ValueError("Backupen saknar datainnehåll.")
    return payload
