"""Organizer-scoped playoff settings and persisted bracket inspection."""
from __future__ import annotations

from cupnavi_core.bracket_validation import validate_bracket_sources
from cupnavi_core.placement_playoffs import DRAW_RULE, all_placement_blocks, placement_tables, source_label
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
TIE_RULES = {"Straffar direkt", "Förlängning + straffar", DRAW_RULE}


def _table_columns(table_name: str) -> set[str]:
    """Return columns for a known internal table, or an empty set if absent.

    Historical CupNavi fixtures intentionally contain only the tables required by
    that release. Participant enrichment and bracket validation are read-model
    enhancements and must not make those older schemas invalid.
    """
    if table_name not in {"teams", "matches", "groups"}:
        raise ValueError("Unsupported schema inspection target")
    with connect() as con:
        rows = con.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {str(row[1]) for row in rows}


def _resolved_playoff_matches(tournament: dict, tournament_id: int) -> list[dict]:
    all_matches = all_rows(
        """SELECT * FROM matches WHERE tournament_id=?
           ORDER BY COALESCE(bracket_id,0),round_no,match_no,id""",
        (int(tournament_id),),
    )
    playoff_matches = [match for match in all_matches if match.get("bracket_id") is not None]

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
    enriched = enrich_match_participants(playoff_matches, resolver)
    group_names = {int(g["id"]): str(g["name"]) for g in all_rows("SELECT id,name FROM groups WHERE tournament_id=?", (int(tournament_id),))}
    for match in enriched:
        for side in ("home", "away"):
            match[f"{side}_source_label"] = source_label(match.get(f"{side}_source"), group_names)
    return enriched


def _bracket_validation(tournament_id: int) -> dict:
    """Validate the current tournament bracket when the modern schema is present."""
    match_columns = _table_columns("matches")
    team_columns = _table_columns("teams")
    group_columns = _table_columns("groups")
    required_match = {"id", "tournament_id", "bracket_id", "home_source", "away_source"}
    if not required_match.issubset(match_columns):
        return {"ready": True, "issue_count": 0, "issues": [], "playoff_match_count": 0, "skipped": True}
    if not {"id", "tournament_id"}.issubset(team_columns) or not {"id", "tournament_id"}.issubset(group_columns):
        return {"ready": True, "issue_count": 0, "issues": [], "playoff_match_count": 0, "skipped": True}
    matches = all_rows("SELECT * FROM matches WHERE tournament_id=?", (int(tournament_id),))
    teams = all_rows("SELECT id FROM teams WHERE tournament_id=?", (int(tournament_id),))
    groups = all_rows("SELECT id FROM groups WHERE tournament_id=?", (int(tournament_id),))
    result = validate_bracket_sources(matches, teams, groups)
    result["skipped"] = False
    return result


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
    validation = _bracket_validation(tournament_id)
    blocks = all_placement_blocks(matches)
    placement_mode = tournament.get("playoff_tie_rule") == DRAW_RULE and bool(blocks)
    tables = []
    if placement_mode:
        from .participant_resolution_repository import tournament_participant_resolver
        resolver = tournament_participant_resolver(tournament)
        groups = all_rows("SELECT id,name FROM groups WHERE tournament_id=?", (int(tournament_id),))
        tables = placement_tables(tournament, matches, {int(g["id"]): g["name"] for g in groups}, resolver)
    return {
        "placement_mode": placement_mode,
        "placement_eligible": bool(blocks),
        "placement_groups": tables,
        "playoff_format": tournament.get("playoff_format") or "Inget slutspel",
        "bronze_match": bool(tournament.get("bronze_match") or 0),
        "playoff_tie_rule": tournament.get("playoff_tie_rule") or "Straffar direkt",
        "playoff_extra_time_minutes": int(tournament.get("playoff_extra_time_minutes", tournament.get("extra_time_minutes", 0)) or 0),
        "brackets": brackets,
        "bracket_count": len(brackets),
        "match_count": len(matches),
        "played_count": played_count,
        "rules_locked": bool(played_count or any(m.get("match_status") in {"live", "halftime", "finished"} for m in matches)),
        "locked_count": locked_count,
        "structure_locked": bool(brackets or matches),
        "bracket_validation": validation,
        "bracket_ready": bool(validation.get("ready", True)),
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
    if tie_rule != "Förlängning + straffar":
        extra_minutes = 0

    structure_change = playoff_format != current["playoff_format"] or bronze_match != current["bronze_match"]
    if structure_change and current["structure_locked"]:
        raise ValueError(
            "Slutspelsstrukturen kan inte ändras när slutspelsträd eller slutspelsmatcher redan finns. Hantera det befintliga slutspelet först"
        )
    if current["rules_locked"] and (
        tie_rule != current["playoff_tie_rule"] or extra_minutes != current["playoff_extra_time_minutes"]
    ):
        raise ValueError("Regler för avgörande kan inte ändras efter att slutspelsmatcher har startats eller spelats")

    converting = tie_rule == DRAW_RULE and current["playoff_tie_rule"] != DRAW_RULE
    if tie_rule == DRAW_RULE and not current["placement_eligible"]:
        raise ValueError("Tabellavgörande kräver kompletta placeringsgrupper där minst tre lag möter varandra en gång. Vinnar-/förlorarkopplingar får inte finnas.")

    with connect() as con:
        con.execute("BEGIN")
        dirty_before = con.execute("SELECT schedule_dirty FROM tournaments WHERE id=?", (int(tournament_id),)).fetchone()[0]
        cursor = con.execute("SELECT * FROM matches WHERE tournament_id=?", (int(tournament_id),))
        columns = [d[0] for d in cursor.description]
        fresh_matches = [dict(zip(columns, row)) for row in cursor.fetchall()]
        if tie_rule == DRAW_RULE and not all_placement_blocks(fresh_matches):
            raise ValueError("Matchschemat har ändrats. Ladda om och kontrollera placeringsgrupperna.")
        if tie_rule != current["playoff_tie_rule"] and any(m.get("bracket_id") is not None and m.get("match_status") in {"live", "halftime", "finished"} for m in fresh_matches):
            raise ValueError("Reglerna kan inte ändras när en slutspelsmatch har startats eller spelats.")
        tournament_columns = {str(row[1]) for row in con.execute("PRAGMA table_info(tournaments)").fetchall()}
        updates = {"playoff_format": playoff_format, "bronze_match": 1 if bronze_match else 0}
        if "playoff_tie_rule" in tournament_columns:
            updates["playoff_tie_rule"] = tie_rule
        for field in ("extra_time_minutes", "playoff_extra_time_minutes"):
            if field in tournament_columns:
                updates[field] = extra_minutes
        if converting:
            updates["bronze_match"] = 0
        rule_change = tie_rule != current["playoff_tie_rule"] or extra_minutes != current["playoff_extra_time_minutes"]
        guard = ""
        params = []
        if rule_change:
            guard = " AND COALESCE(playoff_tie_rule,'Straffar direkt')=? AND NOT EXISTS (SELECT 1 FROM matches WHERE tournament_id=? AND bracket_id IS NOT NULL AND (home_score IS NOT NULL OR away_score IS NOT NULL))"
            params = [current["playoff_tie_rule"], int(tournament_id)]
        revision = ",admin_revision=COALESCE(admin_revision,0)+1" if "admin_revision" in tournament_columns else ""
        cursor = con.execute(
            f"UPDATE tournaments SET {','.join(f'{key}=?' for key in updates)},schedule_dirty=1,is_published=0{revision} WHERE id=?{guard}",
            (*[updates[key] for key in updates], int(tournament_id), *params),
        )
        if getattr(cursor, "rowcount", 1) == 0:
            raise ValueError("Slutspelsreglerna eller resultaten har ändrats. Ladda om innan du sparar igen.")
        if converting:
            for bracket in current["brackets"]:
                sources = {m.get(side) for m in fresh_matches if m.get("bracket_id")==bracket["id"] for side in ("home_source", "away_source")}
                con.execute("UPDATE brackets SET size=?,bronze_match=0 WHERE id=? AND tournament_id=?", (len(sources), bracket["id"], int(tournament_id)))
        if tie_rule == DRAW_RULE:
            # The reviewed schedule and all match times are unchanged. Preserve
            # any pre-existing dirty flag, including on DBs with dirty triggers.
            con.execute("UPDATE tournaments SET schedule_dirty=? WHERE id=?", (dirty_before, int(tournament_id)))
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()
    return admin_playoffs(account_id, tournament_id)
