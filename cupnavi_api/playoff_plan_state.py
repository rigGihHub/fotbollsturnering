"""Revision checks and reversible snapshots for explicit playoff plan changes."""
import hashlib
import json

from cupnavi_core.migrations import ensure_v35_schema_compat
from cupnavi_core.participant_sources import parse_participant_source

SETTINGS = ("playoff_format", "bronze_match", "playoff_tie_rule", "extra_time_minutes", "playoff_extra_time_minutes", "playoff_model_confirmed", "arrangement_type")


def rows(cursor):
    names = [item[0] for item in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def capture_plan_state(con, cup_id, *, playoffs_only=False):
    cup = rows(con.execute("SELECT * FROM tournaments WHERE id=?", (cup_id,)))[0]
    state = {"settings": {key: cup[key] for key in SETTINGS if key in cup},
             "brackets": rows(con.execute("SELECT * FROM brackets WHERE tournament_id=? ORDER BY id", (cup_id,))),
             "matches": rows(con.execute("SELECT * FROM matches WHERE tournament_id=?" + (" AND bracket_id IS NOT NULL" if playoffs_only else "") + " ORDER BY id", (cup_id,)))}
    if not playoffs_only:
        state["cup"] = cup
        for table in ("groups", "teams", "pitches"):
            state[table] = rows(con.execute(f"SELECT * FROM {table} WHERE tournament_id=? ORDER BY " + ("pitch_number" if table == "pitches" else "id"), (cup_id,)))
    return state


def plan_hash(state):
    return hashlib.sha256(json.dumps(state, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def assert_replaceable(state):
    playoffs = [row for row in state["matches"] if row.get("bracket_id") is not None]
    ids = {row["id"] for row in playoffs}
    for match in playoffs:
        if any(match.get(key) is not None for key in ("home_score", "away_score", "home_penalties", "away_penalties", "decided_winner_id")) or match.get("match_status") in {"live", "halftime", "finished"} or match.get("actual_started_at") or match.get("actual_finished_at"):
            raise ValueError(f"Match {match['id']} har startats eller har resultat. Slutspelsformatet kan inte ersättas.")
    for match in state["matches"]:
        if match["id"] not in ids:
            for side in ("home_source", "away_source"):
                source = parse_participant_source(match.get(side))
                if source.kind in {"winner", "loser"} and source.source_id in ids:
                    raise ValueError("En match utanför slutspelet är beroende av det befintliga slutspelsträdet.")


def assert_no_match_events(con, state):
    ids = [row["id"] for row in state["matches"] if row.get("bracket_id") is not None]
    for table in ("player_match_stats", "match_goal_minutes", "match_events"):
        columns = {row[1] for row in con.execute(f"PRAGMA table_info({table})").fetchall()}
        if ids and "match_id" in columns and con.execute(f"SELECT 1 FROM {table} WHERE match_id IN ({','.join('?' for _ in ids)}) LIMIT 1", ids).fetchone():
            raise ValueError("Slutspelet har registrerade matchhändelser. Formatet kan inte ersättas.")


def archive_playoffs(con, cup_id, state):
    assert_no_match_events(con, state)
    ensure_v35_schema_compat(con)
    return {"before": {"settings": state["settings"], "brackets": state["brackets"], "matches": [row for row in state["matches"] if row.get("bracket_id") is not None]}}


def latest_backup(con, cup_id):
    if not con.execute("PRAGMA table_info(tournament_setup_imports)").fetchall():
        return None
    found = rows(con.execute("SELECT id,payload_json FROM tournament_setup_imports WHERE tournament_id=? AND import_kind='playoff_format_backup' ORDER BY id DESC LIMIT 1", (cup_id,)))
    return found[0] if found else None
