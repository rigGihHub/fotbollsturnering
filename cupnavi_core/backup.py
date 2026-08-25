"""Portabel turneringsbackup och kontrollerad återställning."""

import hashlib
import json
import re
from datetime import datetime, timezone

BACKUP_FORMAT_VERSION = 2


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
        payload, ensure_ascii=False, indent=2, sort_keys=True, default=str
    ).encode("utf-8")
    return body, hashlib.sha256(body).hexdigest()


def validate_backup_bytes(data):
    payload = json.loads(data.decode("utf-8"))
    if payload.get("format") != "cupnavi-tournament-backup":
        raise ValueError("Fel backupformat.")
    version = int(payload.get("format_version") or 0)
    if version not in (1, BACKUP_FORMAT_VERSION):
        raise ValueError("Backupversionen stöds inte.")
    if not isinstance(payload.get("data"), dict):
        raise ValueError("Backupen saknar datainnehåll.")
    return payload


def _columns(con, table):
    rows = con.execute(f"PRAGMA table_info({table})").fetchall()
    result = set()
    for row in rows:
        if isinstance(row, dict):
            result.add(row.get("name"))
        elif hasattr(row, "keys"):
            result.add(row["name"])
        else:
            result.add(row[1])
    return {name for name in result if name}


def _insert(con, table, row, overrides=None, drop=("id",)):
    current = _columns(con, table)
    data = dict(row or {})
    data.update(overrides or {})
    for key in drop:
        data.pop(key, None)
    data = {k: v for k, v in data.items() if k in current}
    if not data:
        raise ValueError(f"Inga kompatibla kolumner för {table}.")
    names = list(data)
    cursor = con.execute(
        f"INSERT INTO {table}({','.join(names)}) VALUES({','.join('?' for _ in names)})",
        tuple(data[name] for name in names),
    )
    return getattr(cursor, "lastrowid", None)


def _map_source(source, team_map, group_map, match_map):
    if not source:
        return source
    parts = str(source).split(":")
    try:
        if parts[0] == "team" and len(parts) >= 2:
            parts[1] = str(team_map.get(int(parts[1]), int(parts[1])))
        elif parts[0] == "group" and len(parts) >= 3:
            parts[1] = str(group_map.get(int(parts[1]), int(parts[1])))
        elif parts[0] in ("winner", "loser") and len(parts) >= 2:
            parts[1] = str(match_map.get(int(parts[1]), int(parts[1])))
    except (TypeError, ValueError):
        return source
    return ":".join(parts)


def restore_backup_as_new_tournament(con, payload, *, name=None, environment_type="test"):
    """Återställ backupen som en NY cup. Originalcupen skrivs aldrig över."""
    payload = validate_backup_bytes(
        payload if isinstance(payload, (bytes, bytearray)) else
        json.dumps(payload, ensure_ascii=False).encode("utf-8")
    )
    data = payload["data"]
    if not data.get("tournaments"):
        raise ValueError("Backupen saknar turneringsdata och kan inte återställas.")
    original = dict(data["tournaments"][0])
    environment_type = "test" if environment_type == "test" else "production"

    restored_name = (name or f"{original.get('name') or 'CupNavi'} – återställd").strip()
    tournament_overrides = {
        "name": restored_name,
        "environment_type": environment_type,
        "is_published": 0,
        "lifecycle_status": "draft",
        "public_slug": None,
        "completed_at": None,
        "trashed_at": None,
    }

    class_map, group_map, team_map, player_map = {}, {}, {}, {}
    referee_map, bracket_map, match_map, functionary_map = {}, {}, {}, {}
    subscription_map, notification_map = {}, {}

    try:
        new_tid = _insert(con, "tournaments", original, tournament_overrides)
        if not new_tid:
            row = con.execute(
                "SELECT id FROM tournaments WHERE name=? ORDER BY id DESC LIMIT 1",
                (restored_name,),
            ).fetchone()
            new_tid = row[0] if not hasattr(row, "keys") else row["id"]
        new_tid = int(new_tid)

        def mapped_id(mapping, value):
            if value is None:
                return None
            try:
                return mapping.get(int(value))
            except (TypeError, ValueError):
                return None

        for row in data.get("competition_classes", []):
            old = int(row["id"])
            class_map[old] = int(_insert(con, "competition_classes", row, {"tournament_id": new_tid}))

        for row in data.get("groups", []):
            old = int(row["id"])
            overrides = {"tournament_id": new_tid}
            if "competition_class_id" in row:
                overrides["competition_class_id"] = mapped_id(class_map, row.get("competition_class_id"))
            group_map[old] = int(_insert(con, "groups", row, overrides))

        for row in data.get("teams", []):
            old = int(row["id"])
            overrides = {
                "tournament_id": new_tid,
                "group_id": mapped_id(group_map, row.get("group_id")),
            }
            if "competition_class_id" in row:
                overrides["competition_class_id"] = mapped_id(class_map, row.get("competition_class_id"))
            team_map[old] = int(_insert(con, "teams", row, overrides))

        for row in data.get("players", []):
            old = int(row["id"])
            player_map[old] = int(_insert(
                con, "players", row,
                {"team_id": mapped_id(team_map, row.get("team_id"))},
            ))

        for row in data.get("referees", []):
            old = int(row["id"])
            referee_map[old] = int(_insert(con, "referees", row, {"tournament_id": new_tid}))

        for row in data.get("brackets", []):
            old = int(row["id"])
            bracket_map[old] = int(_insert(con, "brackets", row, {"tournament_id": new_tid}))

        # Matches need two passes because winner/loser sources can point to matches created later.
        pending_sources = []
        for row in data.get("matches", []):
            old = int(row["id"])
            overrides = {
                "tournament_id": new_tid,
                "group_id": mapped_id(group_map, row.get("group_id")),
                "bracket_id": mapped_id(bracket_map, row.get("bracket_id")),
                "referee_id": mapped_id(referee_map, row.get("referee_id")),
                "decided_winner_id": mapped_id(team_map, row.get("decided_winner_id")),
                "home_source": _map_source(row.get("home_source"), team_map, group_map, {}),
                "away_source": _map_source(row.get("away_source"), team_map, group_map, {}),
            }
            new_mid = int(_insert(con, "matches", row, overrides))
            match_map[old] = new_mid
            pending_sources.append((new_mid, row.get("home_source"), row.get("away_source")))

        for new_mid, home_source, away_source in pending_sources:
            con.execute(
                "UPDATE matches SET home_source=?,away_source=? WHERE id=?",
                (
                    _map_source(home_source, team_map, group_map, match_map),
                    _map_source(away_source, team_map, group_map, match_map),
                    new_mid,
                ),
            )

        for row in data.get("schedule_rules", []):
            _insert(con, "schedule_rules", row, {"tournament_id": new_tid}, drop=())
        for table in ("tournament_day_windows", "pitch_day_windows", "pitches", "pitch_travel_times"):
            for row in data.get(table, []):
                _insert(con, table, row, {"tournament_id": new_tid}, drop=())

        for row in data.get("schedule_requests", []):
            _insert(con, "schedule_requests", row, {
                "tournament_id": new_tid,
                "team_id": mapped_id(team_map, row.get("team_id")),
            })

        for row in data.get("player_match_stats", []):
            _insert(con, "player_match_stats", row, {
                "match_id": mapped_id(match_map, row.get("match_id")),
                "player_id": mapped_id(player_map, row.get("player_id")),
            })

        for row in data.get("match_rosters", []):
            _insert(con, "match_rosters", row, {
                "match_id": mapped_id(match_map, row.get("match_id")),
                "team_id": mapped_id(team_map, row.get("team_id")),
                "player_id": mapped_id(player_map, row.get("player_id")),
            }, drop=())

        for row in data.get("functionaries", []):
            old = int(row["id"])
            functionary_map[old] = int(_insert(con, "functionaries", row, {"tournament_id": new_tid}))
        for row in data.get("functionary_shifts", []):
            _insert(con, "functionary_shifts", row, {
                "tournament_id": new_tid,
                "functionary_id": mapped_id(functionary_map, row.get("functionary_id")),
            })

        for table in ("offers", "sponsors", "feedback", "venue_points", "control_incidents"):
            for row in data.get(table, []):
                _insert(con, table, row, {"tournament_id": new_tid})

        for row in data.get("team_messages", []):
            _insert(con, "team_messages", row, {
                "tournament_id": new_tid,
                "sender_team_id": mapped_id(team_map, row.get("sender_team_id")),
                "recipient_team_id": mapped_id(team_map, row.get("recipient_team_id")),
            })

        for row in data.get("participant_access_credentials", []):
            _insert(con, "participant_access_credentials", row, {
                "tournament_id": new_tid,
                "team_id": mapped_id(team_map, row.get("team_id")),
            })

        for row in data.get("notifications", []):
            old = int(row["id"])
            notification_map[old] = int(_insert(con, "notifications", row, {
                "tournament_id": new_tid,
                "team_id": mapped_id(team_map, row.get("team_id")),
            }))

        for row in data.get("notification_subscriptions", []):
            old = int(row["id"])
            subscription_map[old] = int(_insert(con, "notification_subscriptions", row, {
                "tournament_id": new_tid,
                "team_id": mapped_id(team_map, row.get("team_id")),
            }))

        for row in data.get("notification_deliveries", []):
            _insert(con, "notification_deliveries", row, {
                "subscription_id": mapped_id(subscription_map, row.get("subscription_id")),
                "notification_id": mapped_id(notification_map, row.get("notification_id")),
            })

        for row in data.get("cup_feed", []):
            _insert(con, "cup_feed", row, {
                "tournament_id": new_tid,
                "related_match_id": mapped_id(match_map, row.get("related_match_id")),
            })
        for row in data.get("referee_acknowledgements", []):
            _insert(con, "referee_acknowledgements", row, {
                "tournament_id": new_tid,
                "referee_id": mapped_id(referee_map, row.get("referee_id")),
                "match_id": mapped_id(match_map, row.get("match_id")),
            })
        for row in data.get("audit_log", []):
            _insert(con, "audit_log", row, {"tournament_id": new_tid})

        con.commit()
        return new_tid
    except Exception:
        rollback = getattr(con, "rollback", None)
        if rollback:
            rollback()
        raise
