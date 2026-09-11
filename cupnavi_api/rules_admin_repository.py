"""Organizer-scoped competition and scheduling rules for CupNavi."""
from __future__ import annotations

from .admin_repository import _has_tournament_access
from .repository import connect, one

TABLE_TIEBREAKS = {"Målskillnad först", "Inbördes möten först"}
SCHEDULE_FIELDS = (
    "halves",
    "minutes_per_half",
    "halftime_minutes",
    "pitch_break_minutes",
    "minimum_team_rest_minutes",
    "avoid_consecutive_matches",
    "consecutive_match_break_minutes",
)


def _ensure_schedule_rules(tournament_id: int):
    row = one("SELECT * FROM schedule_rules WHERE tournament_id=?", (int(tournament_id),))
    if row:
        return row
    with connect() as con:
        con.execute("INSERT INTO schedule_rules(tournament_id) VALUES(?)", (int(tournament_id),))
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()
    return one("SELECT * FROM schedule_rules WHERE tournament_id=?", (int(tournament_id),)) or {}


def admin_rules(account_id: int, tournament_id: int):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    tournament = one(
        """SELECT id,sport,points_win,points_draw,points_loss,table_tiebreak,schedule_dirty
           FROM tournaments WHERE id=?""",
        (int(tournament_id),),
    )
    if not tournament:
        return None
    rules = _ensure_schedule_rules(tournament_id)
    state = one(
        """SELECT COUNT(*) AS scheduled_count,
                  SUM(CASE WHEN home_score IS NOT NULL AND away_score IS NOT NULL THEN 1 ELSE 0 END) AS completed_count
           FROM matches WHERE tournament_id=?""",
        (int(tournament_id),),
    ) or {}
    halves = int(rules.get("halves") or 2)
    minutes_per_half = int(rules.get("minutes_per_half") or 20)
    halftime_minutes = int(rules.get("halftime_minutes") or 5)
    return {
        "sport": tournament.get("sport") or "Fotboll",
        "points_win": int(tournament.get("points_win") or 0),
        "points_draw": int(tournament.get("points_draw") or 0),
        "points_loss": int(tournament.get("points_loss") or 0),
        "table_tiebreak": tournament.get("table_tiebreak") or "Målskillnad först",
        "halves": halves,
        "minutes_per_half": minutes_per_half,
        "halftime_minutes": halftime_minutes,
        "pitch_break_minutes": int(rules.get("pitch_break_minutes") or 0),
        "minimum_team_rest_minutes": int(rules.get("minimum_team_rest_minutes") or 0),
        "avoid_consecutive_matches": bool(rules.get("avoid_consecutive_matches") if rules.get("avoid_consecutive_matches") is not None else 1),
        "consecutive_match_break_minutes": int(rules.get("consecutive_match_break_minutes") or 0),
        "match_duration_minutes": halves * minutes_per_half + max(0, halves - 1) * halftime_minutes,
        "scheduled_count": int(state.get("scheduled_count") or 0),
        "completed_count": int(state.get("completed_count") or 0),
        "schedule_dirty": bool(tournament.get("schedule_dirty") or 0),
    }


def _integer(values: dict, field: str, current: int, low: int, high: int, label: str) -> int:
    raw = values.get(field, current)
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} måste vara ett heltal") from exc
    if value < low or value > high:
        raise ValueError(f"{label} måste vara mellan {low} och {high}")
    return value


def update_rules(account_id: int, tournament_id: int, values: dict):
    current = admin_rules(account_id, tournament_id)
    if current is None:
        return None

    clean = {
        "halves": _integer(values, "halves", current["halves"], 1, 4, "Antal halvlekar/perioder"),
        "minutes_per_half": _integer(values, "minutes_per_half", current["minutes_per_half"], 1, 90, "Minuter per halvlek/period"),
        "halftime_minutes": _integer(values, "halftime_minutes", current["halftime_minutes"], 0, 30, "Paus mellan halvlekar/perioder"),
        "pitch_break_minutes": _integer(values, "pitch_break_minutes", current["pitch_break_minutes"], 0, 60, "Planpaus mellan matcher"),
        "minimum_team_rest_minutes": _integer(values, "minimum_team_rest_minutes", current["minimum_team_rest_minutes"], 0, 240, "Minsta lagvila"),
        "avoid_consecutive_matches": 1 if bool(values.get("avoid_consecutive_matches", current["avoid_consecutive_matches"])) else 0,
        "consecutive_match_break_minutes": _integer(values, "consecutive_match_break_minutes", current["consecutive_match_break_minutes"], 0, 180, "Extra paus vid raka matcher"),
        "points_win": _integer(values, "points_win", current["points_win"], 0, 10, "Poäng för vinst"),
        "points_draw": _integer(values, "points_draw", current["points_draw"], 0, 10, "Poäng för oavgjort"),
        "points_loss": _integer(values, "points_loss", current["points_loss"], 0, 10, "Poäng för förlust"),
    }
    tiebreak = str(values.get("table_tiebreak", current["table_tiebreak"]) or "").strip()
    if tiebreak not in TABLE_TIEBREAKS:
        raise ValueError("Ogiltig regel för tabellskiljning")
    clean["table_tiebreak"] = tiebreak

    timing_changed = any(clean[field] != current[field] for field in SCHEDULE_FIELDS)
    structure_changed = any(
        clean[field] != current[field]
        for field in ("halves", "minutes_per_half", "halftime_minutes")
    )
    if structure_changed and int(current.get("completed_count") or 0) > 0:
        raise ValueError(
            "Matchstrukturen kan inte ändras när cupen redan har färdigspelade matcher. Resultathistoriken måste behållas konsekvent"
        )

    with connect() as con:
        con.execute(
            """UPDATE schedule_rules SET halves=?,minutes_per_half=?,halftime_minutes=?,pitch_break_minutes=?,
                   minimum_team_rest_minutes=?,avoid_consecutive_matches=?,consecutive_match_break_minutes=?
               WHERE tournament_id=?""",
            (
                clean["halves"], clean["minutes_per_half"], clean["halftime_minutes"],
                clean["pitch_break_minutes"], clean["minimum_team_rest_minutes"],
                clean["avoid_consecutive_matches"], clean["consecutive_match_break_minutes"],
                int(tournament_id),
            ),
        )
        con.execute(
            """UPDATE tournaments SET points_win=?,points_draw=?,points_loss=?,table_tiebreak=?
               WHERE id=?""",
            (
                clean["points_win"], clean["points_draw"], clean["points_loss"],
                clean["table_tiebreak"], int(tournament_id),
            ),
        )
        if timing_changed and int(current.get("scheduled_count") or 0) > 0:
            con.execute("UPDATE tournaments SET schedule_dirty=1 WHERE id=?", (int(tournament_id),))
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()
    return admin_rules(account_id, tournament_id)
