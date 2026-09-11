"""Authenticated publication and match-result administration for the Next admin."""
from __future__ import annotations

from cupnavi_core.admin_publication import build_publish_blockers

from .admin_repository import _has_tournament_access
from .repository import all_rows, connect, one


def _publication_payload(tournament_id: int):
    tournament = one("SELECT * FROM tournaments WHERE id=?", (int(tournament_id),))
    if not tournament:
        return None
    scheduled_row = one(
        "SELECT COUNT(*) AS count FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL",
        (int(tournament_id),),
    )
    scheduled = int((scheduled_row or {}).get("count") or 0)
    blockers = build_publish_blockers(
        playoff_model_confirmed=bool(tournament.get("playoff_format")) if "playoff_format" in tournament else True,
        scheduled_matches=scheduled,
        schedule_dirty=bool(tournament.get("schedule_dirty")) if "schedule_dirty" in tournament else False,
        schedule_errors=(),
    )
    return {
        "tournament": tournament,
        "scheduled_matches": scheduled,
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


def admin_reporting(account_id: int, tournament_id: int):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    matches = all_rows(
        """SELECT id,stage,scheduled_start,pitch_number,home_score,away_score,home_source,away_source
           FROM matches WHERE tournament_id=?
           ORDER BY COALESCE(scheduled_start,''),id""",
        (int(tournament_id),),
    )
    teams = all_rows("SELECT id,name FROM teams WHERE tournament_id=?", (int(tournament_id),))
    teams_by_id = {int(team["id"]): team["name"] for team in teams}
    for match in matches:
        match["home_team"] = _team_name(match.get("home_source"), teams_by_id)
        match["away_team"] = _team_name(match.get("away_source"), teams_by_id)
        match["status"] = "played" if match.get("home_score") is not None and match.get("away_score") is not None else "scheduled"
    return {"matches": matches}


def save_result(
    account_id: int,
    tournament_id: int,
    match_id: int,
    home_score: int,
    away_score: int,
    expected_home,
    expected_away,
):
    if home_score < 0 or away_score < 0:
        raise ValueError("Resultat kan inte vara negativa")
    if not _has_tournament_access(account_id, tournament_id):
        return None
    row = one(
        "SELECT home_score,away_score FROM matches WHERE id=? AND tournament_id=?",
        (int(match_id), int(tournament_id)),
    )
    if not row:
        return None
    if row.get("home_score") != expected_home or row.get("away_score") != expected_away:
        raise RuntimeError("Resultatet har ändrats av någon annan. Ladda om innan du sparar igen.")
    with connect() as conn:
        conn.execute(
            "UPDATE matches SET home_score=?,away_score=? WHERE id=? AND tournament_id=?",
            (int(home_score), int(away_score), int(match_id), int(tournament_id)),
        )
        commit = getattr(conn, "commit", None)
        if callable(commit):
            commit()
    updated = one(
        "SELECT id,home_score,away_score FROM matches WHERE id=? AND tournament_id=?",
        (int(match_id), int(tournament_id)),
    )
    if updated:
        updated["status"] = "played"
    return updated
