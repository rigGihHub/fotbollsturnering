"""Review-first import of playoff structures extracted from cup documents."""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import date, datetime

from cupnavi_core.bracket_validation import validate_bracket_sources
from cupnavi_core.placement_playoffs import DRAW_RULE, all_placement_blocks

from .admin_repository import _has_tournament_access
from .repository import connect, one

_GROUP_SOURCE = re.compile(r"^\s*(\d+)\s*(?::?a|:e|a|e)?\.?\s*(?:i\s+)?grupp\s+(.+?)\s*$", re.I)
_WINNER_SOURCE = re.compile(r"^\s*(?:vinnare|winner)\s*(?:av\s+)?(.+?)\s*$", re.I)
_LOSER_SOURCE = re.compile(r"^\s*(?:förlorare|forlorare|loser)\s*(?:av\s+)?(.+?)\s*$", re.I)


def _dict_rows(cursor) -> list[dict]:
    columns = [str(item[0]) for item in (cursor.description or [])]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


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
            match_time = datetime.strptime(raw, fmt).time()
        except ValueError:
            continue
        if fallback_date is None:
            raise ValueError("En slutspelsmatch har bara klockslag men cupen saknar startdatum. Ange datum innan import.")
        return datetime.combine(fallback_date, match_time).isoformat(timespec="minutes")
    try:
        return datetime.fromisoformat(raw.replace("T", " ")).isoformat(timespec="minutes")
    except ValueError as exc:
        raise ValueError(f"Ogiltig tid i slutspelet: {raw}") from exc


def _snapshot(tournament_id: int) -> dict:
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
    payload = _snapshot(tournament_id)
    matches = [dict(row) for row in (payload.get("playoff_matches") or []) if isinstance(row, dict)]
    existing = one("SELECT COUNT(*) AS n FROM matches WHERE tournament_id=? AND bracket_id IS NOT NULL", (int(tournament_id),))
    brackets = one("SELECT COUNT(*) AS n FROM brackets WHERE tournament_id=?", (int(tournament_id),))
    return {
        "available": bool(matches),
        "source_name": payload.get("source_name"),
        "playoff_matches": matches,
        "playoff_rule_values": payload.get("playoff_rule_values") or {},
        "existing_playoff_matches": int((existing or {}).get("n") or 0),
        "existing_brackets": int((brackets or {}).get("n") or 0),
    }


def _resolve_source(raw_value, team_map, group_map, inserted_labels):
    raw = " ".join(str(raw_value or "").split())
    if not raw:
        return None, "deltagarkälla saknas"
    team_id = team_map.get(raw.casefold())
    if team_id is not None:
        return f"team:{team_id}", None
    group_match = _GROUP_SOURCE.match(raw)
    if group_match:
        group_id = group_map.get(group_match.group(2).strip().casefold())
        if group_id is None:
            return None, f"gruppen '{group_match.group(2).strip()}' finns inte"
        return f"group:{group_id}:{int(group_match.group(1))}", None
    for regex, kind in ((_WINNER_SOURCE, "winner"), (_LOSER_SOURCE, "loser")):
        match = regex.match(raw)
        if match:
            dependency = inserted_labels.get(_normalize_label(match.group(1)))
            return (f"{kind}:{dependency}", None) if dependency is not None else (None, "dependency")
    return None, f"deltagarkällan '{raw}' kan inte tolkas säkert"


def _bracket_size(match_count: int) -> int:
    target = max(2, int(match_count) + 1)
    size = 2
    while size < target:
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

    tournament = one("SELECT id,start_date FROM tournaments WHERE id=?", (int(tournament_id),)) or {}
    fallback_date = None
    if tournament.get("start_date"):
        try:
            fallback_date = date.fromisoformat(str(tournament["start_date"]))
        except ValueError:
            pass

    with connect() as con:
        try:
            if con.execute("SELECT COUNT(*) FROM brackets WHERE tournament_id=?", (int(tournament_id),)).fetchone()[0]:
                raise ValueError("Cupen har redan ett slutspelsträd. Importen avbryts utan att ändra något.")

            teams = con.execute("SELECT id,name FROM teams WHERE tournament_id=?", (int(tournament_id),)).fetchall()
            groups = con.execute("SELECT id,name FROM groups WHERE tournament_id=?", (int(tournament_id),)).fetchall()
            team_map = {str(row[1]).strip().casefold(): int(row[0]) for row in teams}
            group_map = {str(row[1]).strip().casefold(): int(row[0]) for row in groups}
            pitches = con.execute("SELECT pitch_number,name FROM pitches WHERE tournament_id=?", (int(tournament_id),)).fetchall()
            pitch_map = {str(row[1]).strip().casefold(): int(row[0]) for row in pitches}
            next_pitch = max([int(row[0]) for row in pitches] or [0]) + 1

            normalized = []
            seen_matches = set()
            for index, row in enumerate(rows, start=1):
                label = " ".join(str(row.get("label") or f"Slutspelsmatch {index}").split())
                label_key = _normalize_label(label)
                if not label_key:
                    raise ValueError(f"Match {index}: ange ett matchnamn.")
                signature = tuple(" ".join(str(row.get(field) or "").split()).casefold()
                                  for field in ("home_source", "away_source", "time", "venue"))
                if signature in seen_matches:
                    raise ValueError(f"Match {index} ({label}) är en dubblett: samma deltagare, tid och plan. Ta bort dubbletten i underlaget.")
                seen_matches.add(signature)
                normalized.append({**row, "_index": index, "_label": label, "_label_key": label_key})

            label_counts = Counter(row["_label_key"] for row in normalized)
            # A group name may label several placement matches. A winner/loser
            # dependency, however, must identify exactly one match.
            for row in normalized:
                for field in ("home_source", "away_source"):
                    raw = str(row.get(field) or "").strip()
                    if raw.casefold() in team_map:
                        continue
                    dependency = _WINNER_SOURCE.match(raw) or _LOSER_SOURCE.match(raw)
                    if dependency and label_counts[_normalize_label(dependency.group(1))] > 1:
                        raise ValueError(f"Match {row['_index']}: '{raw}' pekar på flera matcher. Ge dessa matcher unika namn och uppdatera hänvisningen.")

            bronze = any(any(word in row["_label"].casefold() for word in ("brons", "3:e", "3e plats", "third")) for row in normalized)
            bracket_cursor = con.execute(
                "INSERT INTO brackets(tournament_id,name,size,bronze_match) VALUES(?,?,?,?)",
                (int(tournament_id), "Importerat slutspel", _bracket_size(len(rows)), 1 if bronze else 0),
            )
            bracket_id = int(getattr(bracket_cursor, "lastrowid", None) or con.execute(
                "SELECT id FROM brackets WHERE tournament_id=? ORDER BY id DESC LIMIT 1", (int(tournament_id),)
            ).fetchone()[0])

            inserted_labels: dict[str, int] = {}
            inserted_rounds: dict[int, int] = {}
            remaining = list(normalized)
            while remaining:
                progress = False
                waiting = []
                for row in remaining:
                    home_source, home_error = _resolve_source(row.get("home_source"), team_map, group_map, inserted_labels)
                    away_source, away_error = _resolve_source(row.get("away_source"), team_map, group_map, inserted_labels)
                    if home_error == "dependency" or away_error == "dependency":
                        waiting.append(row)
                        continue
                    if home_error:
                        raise ValueError(f"{row['_label']}: {home_error}")
                    if away_error:
                        raise ValueError(f"{row['_label']}: {away_error}")

                    dependency_ids = [int(source.split(":", 1)[1]) for source in (home_source, away_source) if source and source.split(":", 1)[0] in {"winner", "loser"}]
                    round_no = 1 + max([inserted_rounds.get(dep, 0) for dep in dependency_ids] or [0])
                    venue = " ".join(str(row.get("venue") or "").split())
                    pitch_number = None
                    if venue:
                        pitch_number = pitch_map.get(venue.casefold())
                        if pitch_number is None:
                            pitch_number = next_pitch
                            next_pitch += 1
                            pitch_map[venue.casefold()] = pitch_number
                            con.execute("INSERT INTO pitches(tournament_id,pitch_number,name) VALUES(?,?,?)", (int(tournament_id), pitch_number, venue))
                    start = _parse_start(row.get("time"), fallback_date)
                    match_cursor = con.execute(
                        """INSERT INTO matches(tournament_id,bracket_id,stage,round_no,match_no,home_source,away_source,scheduled_start,pitch_number,schedule_locked)
                           VALUES(?,?,?,?,?,?,?,?,?,1)""",
                        (int(tournament_id), bracket_id, row["_label"], round_no, int(row["_index"]), home_source, away_source, start, pitch_number),
                    )
                    match_id = int(getattr(match_cursor, "lastrowid", None) or con.execute(
                        "SELECT id FROM matches WHERE tournament_id=? AND bracket_id=? AND match_no=? ORDER BY id DESC LIMIT 1",
                        (int(tournament_id), bracket_id, int(row["_index"])),
                    ).fetchone()[0])
                    if label_counts[row["_label_key"]] == 1:
                        inserted_labels[row["_label_key"]] = match_id
                    inserted_rounds[match_id] = round_no
                    progress = True
                if not progress:
                    raise ValueError("Olösbara slutspelskällor: " + ", ".join(row["_label"] for row in waiting))
                remaining = waiting

            all_matches = _dict_rows(con.execute("SELECT * FROM matches WHERE tournament_id=?", (int(tournament_id),)))
            persisted_teams = _dict_rows(con.execute("SELECT id FROM teams WHERE tournament_id=?", (int(tournament_id),)))
            persisted_groups = _dict_rows(con.execute("SELECT id FROM groups WHERE tournament_id=?", (int(tournament_id),)))
            validation = validate_bracket_sources(all_matches, persisted_teams, persisted_groups)
            if not validation.get("ready"):
                issue = (validation.get("issues") or [{}])[0].get("message") or "Slutspelsträdet är inte giltigt"
                raise ValueError(str(issue))

            rules = dict(playoff_rule_values or {})
            tie_rule = str(rules.get("tie_rule") or "").strip()
            explicit_draw = tie_rule == DRAW_RULE or bool(re.search(r"\balla matcher (?:får|kan) sluta oavgjort\b|\boavgjort (?:är )?tillåtet\b", tie_rule, re.I))
            blocks = all_placement_blocks(all_matches)
            if explicit_draw:
                if not blocks:
                    raise ValueError("Underlaget tillåter oavgjort, men matcherna bildar inte kompletta placeringsgrupper. Kontrollera matcher och deltagarkällor.")
                tie_rule = DRAW_RULE
                bronze = False
                sources = {source for block in blocks for source in block["sources"]}
                con.execute("UPDATE brackets SET size=?,bronze_match=0 WHERE id=? AND tournament_id=?", (len(sources), bracket_id, int(tournament_id)))
            tournament_columns = {str(row[1]) for row in con.execute("PRAGMA table_info(tournaments)").fetchall()}
            updates = ["playoff_format=?", "bronze_match=?", "schedule_dirty=0", "is_published=0", "arrangement_type='tournament_playoffs'", "admin_revision=COALESCE(admin_revision,0)+1"]
            values: list[object] = ["Manuellt slutspel", 1 if bronze else 0]
            if "playoff_model_confirmed" in tournament_columns:
                updates.insert(2, "playoff_model_confirmed=1")
            if tie_rule in {"Straffar direkt", "Förlängning + straffar", DRAW_RULE}:
                updates.append("playoff_tie_rule=?")
                values.append(tie_rule)
            if tie_rule in {DRAW_RULE, "Straffar direkt", "Förlängning + straffar"}:
                extra_minutes = int(rules.get("extra_time_minutes") or 0) if tie_rule == "Förlängning + straffar" else 0
                if not 0 <= extra_minutes <= 60:
                    raise ValueError("Förlängningstiden måste vara mellan 0 och 60 minuter")
                for field in ("extra_time_minutes", "playoff_extra_time_minutes"):
                    if field in tournament_columns:
                        updates.append(f"{field}=?")
                        values.append(extra_minutes)
            con.execute(f"UPDATE tournaments SET {','.join(updates)} WHERE id=?", (*values, int(tournament_id)))
            commit = getattr(con, "commit", None)
            if callable(commit):
                commit()
            return {"imported": len(inserted_rounds), "bracket_id": bracket_id, "validation": validation}
        except Exception:
            rollback = getattr(con, "rollback", None)
            if callable(rollback):
                rollback()
            raise
