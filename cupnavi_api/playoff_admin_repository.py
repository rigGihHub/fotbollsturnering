"""Organizer-scoped playoff settings and persisted bracket inspection."""
from __future__ import annotations

from cupnavi_core.participant_resolution import (
    ParticipantResolver,
    enrich_match_participants,
    finalized_group_standings,
)

from .admin_repository import _has_tournament_access
from .repository import all_rows, connect, one

PLAYOFF_FORMATS = {
    "Inget slutspel",
    "Slutspel – bara ettor och tvåor",
    "A- och B-slutspel",
    "Placeringsslutspel – ettor mot ettor osv.",
    "Manuellt slutspel",
}
TIE_RULES = {"Straffar direkt", "Förlängning + straffar"}


def _table_columns(table_name: str) -> set[str]:
    """Return columns for a known internal table, or an empty set if absent.

    Historical CupNavi fixtures intentionally contain only the tables required by
    that release. Participant enrichment is a read-model enhancement and must not
    make those older schemas invalid.
    """
    if table_name not in {"teams", "matches"}:
        raise ValueError("Unsupported schema inspection target")
    with connect() as con:
        rows = con.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {str(row[1]) for row in rows}


def _resolved_playoff_matches(tournament: dict, tournament_id: int) -> list[dict]:
    # SELECT * is intentional here: historical match schemas have fewer columns
    # than current production. The resolver reads optional fields with dict.get,
    # while the legacy read model remains valid without synthetic columns.
    all_matches = all_rows(
        """SELECT * FROM matches WHERE tournament_id=?
           ORDER BY COALESCE(bracket_id,0),round_no,match_no,id""",
        (int(tournament_id),),
    )
    playoff_matches = [match for match in all_matches if match.get("bracket_id") is not None]

    # v634-era/minimal fixtures can legitimately lack a teams table. In that
    # schema shape we preserve the historical raw playoff read model instead of
    # failing an otherwise valid cup.
    team_columns = _table_columns("teams")
    if not {"id", "name", "group_id", "tournament_id"}.issubset(team_columns):
        return playoff_matches

    teams = all_rows(
        "SELECT id,name,group_id FROM teams WHERE tournament_id=? ORDER BY name,id",
        (int(tournament_id),),
    )
    standings = finalized_group_standings(
        teams,
        all_matches,
        points_win=int(tournament.get("points_win") or 0),
        points_draw=int(tournament.get("points_draw") or 0),
        points_loss=int(tournament.get("points_loss") or 0),
        table_tiebreak=str(tournament.get("table_tiebreak") or "Målskillnad först"),
    )
    resolver = ParticipantResolver(teams=teams, matches=all_matches, standings_by_group=standings)
    return enrich_match_participants(playoff_matches, resolver)


def admin_playoffs(account_id: int, tournament_id: int):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    tournament = one("SELECT * FROM tournaments WHERE id=?", (int(tournament_id),))
    if not tournament:
        return None
    brackets = all_rows(
        "SELECT id,name,size,bronze_match FROM brackets WHERE tournament_id=? ORDER BY id",
        (int(tournament_id),),
    )
    matches = _resolved_playoff_matches(tournament, tournament_id)
    by_bracket = {}
    for match in matches:
        by_bracket.setdefault(int(match["bracket_id"]), []).append(match)
    for bracket in brackets:
        bracket["matches"] = by_bracket.get(int(bracket["id"]), [])
    played_count = sum(1 for match in matches if match.get("home_score") is not None and match.get("away_score") is not None)
    locked_count = sum(1 for match in matches if bool(match.get("schedule_locked") or 0))
    return {
        "playoff_format": tournament.get("playoff_format") or "Inget slutspel",
        "bronze_match": bool(tournament.get("bronze_match") or 0),
        "playoff_tie_rule": tournament.get("playoff_tie_rule") or "Straffar direkt",
        "playoff_extra_time_minutes": int(tournament.get("playoff_extra_time_minutes") or 0),
        "brackets": brackets,
        "bracket_count": len(brackets),
        "match_count": len(matches),
        "played_count": played_count,
        "locked_count": locked_count,
        "structure_locked": bool(brackets or matches),
    }


def update_playoff_settings(account_id: int, tournament_id: int, values: dict):
    current = admin_playoffs(account_id, tournament_id)
    if current is None:
        return None
    playoff_format = str(values.get("playoff_format", current["playoff_format"]) or "").strip()
    if playoff_format not in PLAYOFF_FORMATS:
        raise ValueError("Ogiltigt slutspelsformat")
    bronze_match = bool(values.get("bronze_match", current["bronze_match"]))
    tie_rule = str(values.get("playoff_tie_rule", current["playoff_tie_rule"]) or "").strip()
    if tie_rule not in TIE_RULES:
        raise ValueError("Ogiltig regel vid oavgjort slutspelsresultat")
    try:
        extra_minutes = int(values.get("playoff_extra_time_minutes", current["playoff_extra_time_minutes"]) or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError("Förlängningstid måste vara ett heltal") from exc
    if extra_minutes < 0 or extra_minutes > 60:
        raise ValueError("Förlängningstid måste vara mellan 0 och 60 minuter")
    if tie_rule == "Straffar direkt":
        extra_minutes = 0

    structure_change = playoff_format != current["playoff_format"] or bronze_match != current["bronze_match"]
    if structure_change and current["structure_locked"]:
        raise ValueError(
            "Slutspelsstrukturen kan inte ändras när slutspelsträd eller slutspelsmatcher redan finns. Hantera det befintliga slutspelet först"
        )
    if current["played_count"] and (
        tie_rule != current["playoff_tie_rule"] or extra_minutes != current["playoff_extra_time_minutes"]
    ):
        raise ValueError("Regler för avgörande kan inte ändras efter att slutspelsmatcher har spelats")

    with connect() as con:
        tournament_columns = {str(row[1]) for row in con.execute("PRAGMA table_info(tournaments)").fetchall()}
        updates = {"playoff_format": playoff_format, "bronze_match": 1 if bronze_match else 0}
        if "playoff_tie_rule" in tournament_columns:
            updates["playoff_tie_rule"] = tie_rule
        if "playoff_extra_time_minutes" in tournament_columns:
            updates["playoff_extra_time_minutes"] = extra_minutes
        con.execute(
            f"UPDATE tournaments SET {','.join(f'{key}=?' for key in updates)},schedule_dirty=1,is_published=0 WHERE id=?",
            (*[updates[key] for key in updates], int(tournament_id)),
        )
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()
    return admin_playoffs(account_id, tournament_id)
