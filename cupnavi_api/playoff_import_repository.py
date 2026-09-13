"""Review-first import of playoff structures extracted from cup documents."""
from __future__ import annotations

import json
import re
from datetime import date, datetime

from cupnavi_core.bracket_validation import validate_bracket_sources

from .admin_repository import _has_tournament_access
from .repository import all_rows, connect, one


_GROUP_SOURCE = re.compile(
    r"^\s*(\d+)\s*(?::?a|:e|a|e)?\.?\s*(?:i\s+)?grupp\s+(.+?)\s*$",
    re.IGNORECASE,
)
_WINNER_SOURCE = re.compile(r"^\s*(?:vinnare|winner)\s*(?:av\s+)?(.+?)\s*$", re.IGNORECASE)
_LOSER_SOURCE = re.compile(r"^\s*(?:förlorare|forlorare|loser)\s*(?:av\s+)?(.+?)\s*$", re.IGNORECASE)


def _normalize_label(value) -> str:
    text = str(value or "").strip().casefold()
    text = text.replace("semifinal", "semi").replace("kvartsfinal", "kvart")
    text = re.sub(r"\bmatch\b", " ", text)
    text = re.sub(r"[^0-9a-zåäö]+", " ", text)
    return " ".join(text.split())


def _parse_start(value, fallback_date: date | None):
    raw = str(value or "").strip()
    if not raw:
        return None
    for fmt in ("%H:%M", "%H.%M"):
        try:
            parsed_time = datetime.strptime(raw, fmt).time()
        except ValueError:
            continue
        if fallback_date is None:
            raise ValueError("En slutspelsmatch har bara klockslag men cupen saknar startdatum. Ange datum innan import.")
        return datetime.combine(fallback_date, parsed_time).isoformat(timespec="minutes")
    try:
        return datetime.fromisoformat(raw.replace("T", " ")).isoformat(timespec="minutes")
    except ValueError as exc:
        raise ValueError(f"Ogiltig tid i slutspelet: {raw}") from exc


def _review_snapshot(tournament_id: int) -> dict:
    row = one(
        """SELECT payload_json,source_name FROM tournament_setup_imports
           WHERE tournament_id=? AND import_kind='initial_setup'
           ORDER BY id DESC LIMIT 1""",
        (int(tournament_id),),
    )
    if not row:
        return {}
    try:
        payload = json.loads(str(row.get("payload_json") or "{}"))
    except (TypeError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    payload.setdefault("source_name", row.get("source_name"))
    return payload


def playoff_import_review(account_id: int, tournament_id: int):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    snapshot = _review_snapshot(tournament_id)
    rows = [dict(row) for row in (snapshot.get("playoff_matches") or []) if isinstance(row, dict)]
    existing = one(
        "SELECT COUNT(*) AS n FROM matches WHERE tournament_id=? AND bracket_id IS NOT NULL",
        (int(tournament_id),),
    )
    bracket_count = one("SELECT COUNT(*) AS n FROM brackets WHERE tournament_id=?", (int(tournament_id),))
    return {
        "available": bool(rows),
        "source_name": snapshot.get("source_name"),
        "playoff_matches": rows,
        "playoff_rule_values": snapshot.get("playoff_rule_values") or {},
        "existing_playoff_matches": int((existing or {}).get("n") or 0),
        "existing_brackets": int((bracket_count or {}).get("n") or 0),
    }


def _source_resolver(team_map, group_map, inserted_labels):
    def resolve(raw_value):
        raw = " ".join(str(raw_value or "").split())
        if not raw:
            return None, None
        team = team_map.get(raw.casefold())
        if team is not None:
            return f"team:{team}", None
        group_match = _GROUP_SOURCE.match(raw)
        if group_match:
            placement = int(group_match.group(1))
            group_name = group_match.group(2).strip().casefold()
            group_id = group_map.get(group_name)
            if group_id is None:
                return None, f"gruppen '{group_match.group(2).strip()}' finns inte"
            return f"group:{group_id}:{placement}", None
        for regex, kind in ((_WINNER_SOURCE, "winner"), (_LOSER_SOURCE, "loser")):
            match = regex.match(raw)
            if match:
                label_key = _normalize_label(match.group(1))
                dependency = inserted_labels.get(label_key)
                if dependency is None:
                    return None, "dependency"
                return f"{kind}:{dependency}", None
        return None, f"deltagarkällan '{raw}' kan inte tolkas säkert"
    return resolve


def _bracket_size(match_count: int) -> int:
    participants = max(2, int(match_count) + 1)
    size = 2
    while size < participants:
        size *= 2
    return size


def commit_playoff_import(account_id: int, tournament_id: int, playoff_matches: list[dict], playoff_rule_values: dict | None = None):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    rows = [dict(row) for row in (playoff_matches or []) if isinstance(row, dict)]
    if not rows:
        raise ValueError("Det finns inga granskade slutspelsmatcher att importera")
    if len(rows) > 128:
        raise ValueError("Högst 128 slutspelsmatcher kan importeras åt gången")

    tournament = one("SELECT id,start_date FROM tournaments WHERE id=?", (int(tournament_id),))
    fallback_date = None
    if tournament and tournament.get("start_date"):
        try:
            fallback_date = date.fromisoformat(str(tournament["start_date"]))
        except ValueError:
            fallback_date = None

    con = connect()
    try:
        if con.execute("SELECT COUNT(*) FROM brackets WHERE tournament_id=?", (int(tournament_id),)).fetchone()[0]:
            raise ValueError("Cupen har redan ett slutspelsträd. Importen avbryts utan att ändra något.")
        if con.execute("SELECT COUNT(*) FROM matches WHERE tournament_id=? AND bracket_id IS NOT NULL", (int(tournament_id),)).fetchone()[0]:
            raise ValueError("Cupen har redan slutspelsmatcher. Importen avbryts utan att ändra något.")

        teams = con.execute("SELECT id,name FROM teams WHERE tournament_id=?", (int(tournament_id),)).fetchall()
        groups = con.execute("SELECT id,name FROM groups WHERE tournament_id=?", (int(tournament_id),)).fetchall()
        team_map = {str(row[1]).strip().casefold(): int(row[0]) for row in teams}
        group_map = {str(row[1]).strip().casefold(): int(row[0]) for row in groups}

        pitch_rows = con.execute("SELECT pitch_number,name FROM pitches WHERE tournament_id=?", (int(tournament_id),)).fetchall()
        pitch_map = {str(row[1]).strip().casefold(): int(row[0]) for row in pitch_rows}
        next_pitch = max([int(row[0]) for row in pitch_rows] or [0]) + 1

        labels = {}
        normalized_rows = []
        for index, row in enumerate(rows, start=1):
            label = " ".join(str(row.get("label") or f"Slutspelsmatch {index}").split())
            label_key = _normalize_label(label)
            if not label_key:
                raise ValueError(f"Slutspelsmatch {index} saknar matchnamn")
            if label_key in labels:
                raise ValueError(f"Slutspelet innehåller dubbla matchnamn: {label}")
            labels[label_key] = index
            normalized_rows.append({**row, "_index": index, "_label": label, "_label_key": label_key})

        bronze = any(
            any(term in str(row["_label"]).casefold() for term in ("brons", "3:e", "3e plats", "third"))
            for row in normalized_rows
        )
        cursor = con.execute(
            "INSERT INTO brackets(tournament_id,name,size,bronze_match) VALUES(?,?,?,?)",
            (int(tournament_id), "Importerat slutspel", _bracket_size(len(rows)), 1 if bronze else 0),
        )
        bracket_id = getattr(cursor, "lastrowid", None)
        if not bracket_id:
            bracket_id = con.execute(
                "SELECT id FROM brackets WHERE tournament_id=? ORDER BY id DESC LIMIT 1", (int(tournament_id),)
            ).fetchone()[0]
        bracket_id = int(bracket_id)

        inserted_labels: dict[str, int] = {}
        inserted_rounds: dict[int, int] = {}
        remaining = list(normalized_rows)
        while remaining:
            progress = False
            next_remaining = []
            resolver = _source_resolver(team_map, group_map, inserted_labels)
            for row in remaining:
                home_source, home_error = resolver(row.get("home_source"))
                away_source, away_error = resolver(row.get("away_source"))
                dependency_pending = home_error == "dependency" or away_error == "dependency"
                if dependency_pending:
                    next_remaining.append(row)
                    continue
                if home_error:
                    raise ValueError(f"{row['_label']}: {home_error}")
                if away_error:
                    raise ValueError(f"{row['_label']}: {away_error}")
                if not home_source or not away_source:
                    raise ValueError(f"{row['_label']}: båda deltagarkällorna måste vara angivna")

                dependency_ids = []
                for source in (home_source, away_source):
                    if source.startswith("winner:") or source.startswith("loser:"):
                        dependency_ids.append(int(source.split(":", 1)[1]))
                round_no = 1 + max([inserted_rounds.get(dep, 0) for dep in dependency_ids] or [0])

                venue = " ".join(str(row.get("venue") or "").split())
                pitch_number = None
                if venue:
                    pitch_number = pitch_map.get(venue.casefold())
                    if pitch_number is None:
                        pitch_number = next_pitch
                        next_pitch += 1
                        pitch_map[venue.casefold()] = pitch_number
                        con.execute(
                            "INSERT INTO pitches(tournament_id,pitch_number,name) VALUES(?,?,?)",
                            (int(tournament_id), pitch_number, venue),
                        )
                scheduled_start = _parse_start(row.get("time"), fallback_date)
                match_cursor = con.execute(
                    """INSERT INTO matches(
                           tournament_id,bracket_id,stage,round_no,match_no,home_source,away_source,
                           scheduled_start,pitch_number,schedule_locked
                       ) VALUES(?,?,?,?,?,?,?,?,?,1)""",
                    (
                        int(tournament_id), bracket_id, row["_label"], round_no, int(row["_index"]),
                        home_source, away_source, scheduled_start, pitch_number,
                    ),
                )
                match_id = getattr(match_cursor, "lastrowid", None)
                if not match_id:
                    match_id = con.execute(
                        "SELECT id FROM matches WHERE tournament_id=? AND bracket_id=? AND match_no=? ORDER BY id DESC LIMIT 1",
                        (int(tournament_id), bracket_id, int(row["_index"])),
                    ).fetchone()[0]
                match_id = int(match_id)
                inserted_labels[row["_label_key"]] = match_id
                inserted_rounds[match_id] = round_no
                progress = True
            if not progress:
                unresolved = ", ".join(str(row["_label"]) for row in next_remaining)
                raise ValueError(
                    "Slutspelskällorna bildar en olösbar kedja eller hänvisar till matchnamn som inte finns: " + unresolved
                )
            remaining = next_remaining

        persisted = [
            dict(zip([col[0] for col in cursor.description], values))
            for cursor in [con.execute("SELECT * FROM matches WHERE tournament_id=?", (int(tournament_id),))]
            for values in cursor.fetchall()
        ]
        persisted_teams = [dict(zip([col[0] for col in cursor.description], values)) for cursor in [con.execute("SELECT id FROM teams WHERE tournament_id=?", (int(tournament_id),))] for values in cursor.fetchall()]
        persisted_groups = [dict(zip([col[0] for col in cursor.description], values)) for cursor in [con.execute("SELECT id FROM groups WHERE tournament_id=?", (int(tournament_id),))] for values in cursor.fetchall()]
        validation = validate_bracket_sources(persisted, persisted_teams, persisted_groups)
        if not validation.get("ready"):
            first_issue = (validation.get("issues") or [{}])[0].get("message") or "Slutspelsträdet är inte giltigt"
            raise ValueError(str(first_issue))

        rules = dict(playoff_rule_values or {})
        tie_rule = str(rules.get("tie_rule") or "").strip()
        allowed_tie_rules = {"Straffar direkt", "Förlängning + straffar"}
        updates = ["playoff_format=?", "bronze_match=?", "schedule_dirty=0", "is_published=0"]
        values: list[object] = ["Manuellt slutspel", 1 if bronze else 0]
        if tie_rule in allowed_tie_rules:
            updates.append("playoff_tie_rule=?")
            values.append(tie_rule)
        extra = rules.get("extra_time_minutes")
        if tie_rule == "Förlängning + straffar" and extra is not None:
            try:
                extra_minutes = int(extra)
            except (TypeError, ValueError):
                raise ValueError("Förlängningstiden i importunderlaget är ogiltig")
            if extra_minutes < 0 or extra_minutes > 60:
                raise ValueError("Förlängningstiden måste vara mellan 0 och 60 minuter")
            updates.append("playoff_extra_time_minutes=?")
            values.append(extra_minutes)
        con.execute(
            f"UPDATE tournaments SET {','.join(updates)} WHERE id=?",
            (*values, int(tournament_id)),
        )
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()
        return {
            "imported": len(inserted_labels),
            "bracket_id": bracket_id,
            "validation": validation,
        }
    except Exception:
        rollback = getattr(con, "rollback", None)
        if callable(rollback):
            rollback()
        raise
    finally:
        con.close()
