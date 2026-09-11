"""Authenticated publication and match-result administration for the Next admin."""
from __future__ import annotations

from cupnavi_core.db import get_conn
from cupnavi_core.admin_publication import build_publication_checklist
from cupnavi_core.admin_results_repository import update_match_result_if_unchanged


def _owns(conn, account_id: int, tournament_id: int) -> bool:
    row = conn.execute(
        "SELECT 1 FROM tournament_members WHERE tournament_id=? AND account_id=? LIMIT 1",
        (int(tournament_id), int(account_id)),
    ).fetchone()
    return bool(row)


def admin_publication(account_id: int, tournament_id: int):
    with get_conn() as conn:
        if not _owns(conn, account_id, tournament_id): return None
        tournament = conn.execute("SELECT * FROM tournaments WHERE id=?", (int(tournament_id),)).fetchone()
        if not tournament: return None
        checklist = build_publication_checklist(conn, int(tournament_id))
        return {"tournament": dict(tournament), "checklist": checklist, "ready": all(bool(x.get("ok")) for x in checklist)}


def set_publication(account_id: int, tournament_id: int, published: bool):
    with get_conn() as conn:
        if not _owns(conn, account_id, tournament_id): return None
        if published:
            checklist = build_publication_checklist(conn, int(tournament_id))
            failed = [x.get("label") or x.get("key") or "kontroll" for x in checklist if not x.get("ok")]
            if failed: raise ValueError("Cupen kan inte publiceras ännu: " + ", ".join(failed))
        conn.execute("UPDATE tournaments SET is_published=? WHERE id=?", (1 if published else 0, int(tournament_id)))
        conn.commit()
    return admin_publication(account_id, tournament_id)


def admin_reporting(account_id: int, tournament_id: int):
    with get_conn() as conn:
        if not _owns(conn, account_id, tournament_id): return None
        rows = conn.execute("""
            SELECT m.id,m.stage,m.scheduled_start,m.pitch_number,m.home_score,m.away_score,m.status,
                   h.name AS home_team,a.name AS away_team
            FROM matches m JOIN teams h ON h.id=m.home_team_id JOIN teams a ON a.id=m.away_team_id
            WHERE m.tournament_id=? ORDER BY COALESCE(m.scheduled_start,''),m.id
        """, (int(tournament_id),)).fetchall()
        return {"matches": [dict(row) for row in rows]}


def save_result(account_id: int, tournament_id: int, match_id: int, home_score: int, away_score: int, expected_home, expected_away):
    if home_score < 0 or away_score < 0: raise ValueError("Resultat kan inte vara negativa")
    with get_conn() as conn:
        if not _owns(conn, account_id, tournament_id): return None
        match = conn.execute("SELECT * FROM matches WHERE id=? AND tournament_id=?", (int(match_id), int(tournament_id))).fetchone()
        if not match: return None
        ok = update_match_result_if_unchanged(conn, int(match_id), int(home_score), int(away_score), expected_home, expected_away)
        if not ok: raise RuntimeError("Resultatet har ändrats av någon annan. Ladda om innan du sparar igen.")
        conn.execute("UPDATE matches SET status='played' WHERE id=?", (int(match_id),))
        conn.commit()
        row = conn.execute("SELECT id,home_score,away_score,status FROM matches WHERE id=?", (int(match_id),)).fetchone()
        return dict(row)
