"""Authenticated publication and match-result administration for the Next admin."""
from __future__ import annotations

from cupnavi_core.admin_publication import build_publish_blockers
from cupnavi_core.playoff_dependency_safety import (
    build_dependency_guidance,
    dependency_impact,
    transitive_downstream_match_ids,
    winner_side,
)
from cupnavi_core.playoff_result_progression import (
    decided_side_from_team_id,
    prepare_result,
)

from .admin_repository import _has_tournament_access
from .participant_resolution_repository import tournament_participant_resolver
from .repository import all_rows, connect, one
from .schedule_conflicts import analyze_schedule_conflicts


def _schedule_publication_analysis(tournament_id: int) -> dict:
    rules = one(
        """SELECT halves,minutes_per_half,halftime_minutes,pitch_break_minutes,
                  minimum_team_rest_minutes
           FROM schedule_rules WHERE tournament_id=?""",
        (int(tournament_id),),
    ) or {
        "halves": 2,
        "minutes_per_half": 20,
        "halftime_minutes": 5,
        "pitch_break_minutes": 0,
        "minimum_team_rest_minutes": 0,
    }
    group_rows = all_rows(
        "SELECT id,name FROM groups WHERE tournament_id=?",
        (int(tournament_id),),
    )
    group_names = {int(row["id"]): str(row["name"]) for row in group_rows}
    matches = all_rows(
        "SELECT * FROM matches WHERE tournament_id=?",
        (int(tournament_id),),
    )
    for match in matches:
        group_id = match.get("group_id")
        match["group_name"] = group_names.get(int(group_id)) if group_id is not None else None
    return analyze_schedule_conflicts(matches, rules)


def _publication_payload(tournament_id: int):
    tournament = one("SELECT * FROM tournaments WHERE id=?", (int(tournament_id),))
    if not tournament:
        return None
    scheduled_row = one(
        "SELECT COUNT(*) AS count FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL",
        (int(tournament_id),),
    )
    scheduled = int((scheduled_row or {}).get("count") or 0)
    conflict_analysis = _schedule_publication_analysis(tournament_id)
    schedule_errors = tuple(
        item["message"]
        for item in conflict_analysis.get("conflicts", [])
        if item.get("severity") == "error"
    )
    blockers = build_publish_blockers(
        playoff_model_confirmed=bool(tournament.get("playoff_format")) if "playoff_format" in tournament else True,
        scheduled_matches=scheduled,
        schedule_dirty=bool(tournament.get("schedule_dirty")) if "schedule_dirty" in tournament else False,
        schedule_errors=schedule_errors,
    )
    return {
        "tournament": tournament,
        "scheduled_matches": scheduled,
        "schedule_conflict_analysis": conflict_analysis,
        "blockers": blockers,
        "ready": not blockers,
    }


def admin_publication(account_id: int, tournament_id: int):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    return _publication_payload(tournament_id)


def set_publication(account_id: int, tournament_id: int, published: bool):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    state = _publication_payload(tournament_id)
    if state is None:
        return None
    if published and state["blockers"]:
        raise ValueError("Cupen kan inte publiceras ännu: " + " ".join(state["blockers"]))
    with connect() as conn:
        conn.execute(
            "UPDATE tournaments SET is_published=? WHERE id=?",
            (1 if published else 0, int(tournament_id)),
        )
        commit = getattr(conn, "commit", None)
        if callable(commit):
            commit()
    return _publication_payload(tournament_id)


def _team_name(source, teams_by_id):
    if not source:
        return None
    text = str(source)
    if text.startswith("team:"):
        try:
            return teams_by_id.get(int(text.split(":", 1)[1])) or text
        except ValueError:
            return text
    return text


def _resolver_for_tournament(tournament_id: int):
    tournament = one("SELECT * FROM tournaments WHERE id=?", (int(tournament_id),))
    if not tournament:
        return None
    try:
        return tournament_participant_resolver(tournament)
    except Exception:
        # Legacy/minimal fixtures do not necessarily contain the complete modern
        # participant-resolution schema. Reporting remains usable without enrichment.
        return None


def admin_reporting(account_id: int, tournament_id: int):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    matches = all_rows(
        "SELECT * FROM matches WHERE tournament_id=? ORDER BY COALESCE(scheduled_start,''),id",
        (int(tournament_id),),
    )
    teams = all_rows("SELECT id,name FROM teams WHERE tournament_id=?", (int(tournament_id),))
    teams_by_id = {int(team["id"]): team["name"] for team in teams}
    resolver = _resolver_for_tournament(tournament_id)
    for match in matches:
        home = resolver.resolve(match.get("home_source")) if resolver else None
        away = resolver.resolve(match.get("away_source")) if resolver else None
        match["home_team"] = home.team_name if home and home.resolved else _team_name(match.get("home_source"), teams_by_id)
        match["away_team"] = away.team_name if away and away.resolved else _team_name(match.get("away_source"), teams_by_id)
        match["home_team_id"] = home.team_id if home and home.resolved else None
        match["away_team_id"] = away.team_id if away and away.resolved else None
        scores_present = match.get("home_score") is not None and match.get("away_score") is not None
        if not scores_present:
            match["status"] = "scheduled"
        elif str(match.get("stage") or "") != "Gruppspel" and winner_side(
            home_score=match.get("home_score"),
            away_score=match.get("away_score"),
            home_penalties=match.get("home_penalties"),
            away_penalties=match.get("away_penalties"),
            decided_winner_side=decided_side_from_team_id(
                match.get("decided_winner_id"),
                home_team_id=match["home_team_id"],
                away_team_id=match["away_team_id"],
            ),
        ) is None:
            match["status"] = "awaiting_decision"
        else:
            match["status"] = "played"
    return {"matches": matches}


def _row_value(row, key, default=None):
    return row.get(key, default)


def _event_counts(match_ids: tuple[int, ...]) -> dict[int, int]:
    if not match_ids:
        return {}
    placeholders = ",".join("?" for _ in match_ids)
    try:
        rows = all_rows(
            f"SELECT match_id,COUNT(*) AS count FROM player_match_stats WHERE match_id IN ({placeholders}) GROUP BY match_id",
            tuple(int(value) for value in match_ids),
        )
    except Exception:
        return {}
    return {int(row["match_id"]): int(row.get("count") or 0) for row in rows}


def save_result(
    account_id: int,
    tournament_id: int,
    match_id: int,
    home_score: int,
    away_score: int,
    expected_home,
    expected_away,
    *,
    home_penalties=None,
    away_penalties=None,
    expected_home_penalties=None,
    expected_away_penalties=None,
):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    row = one(
        "SELECT * FROM matches WHERE id=? AND tournament_id=?",
        (int(match_id), int(tournament_id)),
    )
    if not row:
        return None
    if (
        row.get("home_score") != expected_home
        or row.get("away_score") != expected_away
        or row.get("home_penalties") != expected_home_penalties
        or row.get("away_penalties") != expected_away_penalties
    ):
        raise RuntimeError("Resultatet har ändrats av någon annan. Ladda om innan du sparar igen.")

    resolver = _resolver_for_tournament(tournament_id)
    home = resolver.resolve(row.get("home_source")) if resolver else None
    away = resolver.resolve(row.get("away_source")) if resolver else None
    home_team_id = home.team_id if home and home.resolved else None
    away_team_id = away.team_id if away and away.resolved else None

    old_manual_side = decided_side_from_team_id(
        row.get("decided_winner_id"),
        home_team_id=home_team_id,
        away_team_id=away_team_id,
    )
    old_side = winner_side(
        home_score=row.get("home_score"),
        away_score=row.get("away_score"),
        home_penalties=row.get("home_penalties"),
        away_penalties=row.get("away_penalties"),
        decided_winner_side=old_manual_side,
    ) if str(row.get("stage") or "") != "Gruppspel" else None

    prepared = prepare_result(
        stage=row.get("stage"),
        home_score=home_score,
        away_score=away_score,
        home_penalties=home_penalties,
        away_penalties=away_penalties,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
    )

    new_decided_winner_id = None
    new_side = prepared.winner_side
    # Preserve an existing explicit/manual tiebreak only while the replacement
    # result remains tied and no penalty result has superseded it.
    if (
        str(row.get("stage") or "") != "Gruppspel"
        and prepared.home_score == prepared.away_score
        and prepared.home_penalties is None
        and old_manual_side is not None
    ):
        new_side = old_manual_side
        new_decided_winner_id = row.get("decided_winner_id")

    all_matches = all_rows("SELECT * FROM matches WHERE tournament_id=?", (int(tournament_id),))
    descendant_ids = transitive_downstream_match_ids(int(match_id), all_matches, row_value=_row_value)
    if old_side != new_side and descendant_ids:
        counts = _event_counts(descendant_ids)
        downstream = []
        wanted = set(descendant_ids)
        for item in all_matches:
            if int(item.get("id") or 0) in wanted:
                item["event_count"] = counts.get(int(item["id"]), 0)
                downstream.append(item)
        impact = dependency_impact(
            old_winner_side=old_side,
            new_winner_side=new_side,
            downstream_rows=downstream,
            row_value=_row_value,
        )
        if impact.blocked:
            locked = [item for item in downstream if int(item.get("id") or 0) in set(impact.downstream_match_ids)]
            guidance = build_dependency_guidance(locked, row_value=_row_value)
            detail = " ".join(guidance) if guidance else impact.reason
            raise RuntimeError(f"{impact.reason} {detail}".strip())

    with connect() as conn:
        conn.execute(
            """UPDATE matches
               SET home_score=?,away_score=?,home_penalties=?,away_penalties=?,decided_winner_id=?
               WHERE id=? AND tournament_id=?""",
            (
                prepared.home_score,
                prepared.away_score,
                prepared.home_penalties,
                prepared.away_penalties,
                new_decided_winner_id,
                int(match_id),
                int(tournament_id),
            ),
        )
        commit = getattr(conn, "commit", None)
        if callable(commit):
            commit()

    updated = one(
        """SELECT id,stage,home_source,away_source,home_score,away_score,
                  home_penalties,away_penalties,decided_winner_id
           FROM matches WHERE id=? AND tournament_id=?""",
        (int(match_id), int(tournament_id)),
    )
    if updated:
        updated["status"] = "played" if (str(updated.get("stage") or "") == "Gruppspel" or new_side is not None) else "awaiting_decision"
        updated["outcome_resolved"] = str(updated.get("stage") or "") == "Gruppspel" or new_side is not None
        updated["winner_side"] = new_side
        updated["winner_team_id"] = home_team_id if new_side == "home" else away_team_id if new_side == "away" else None
    return updated
