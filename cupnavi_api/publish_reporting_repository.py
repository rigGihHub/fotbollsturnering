"""Authenticated publication and match-result administration for the Next admin."""
from __future__ import annotations
from cupnavi_core.db import get_conn
from cupnavi_core.admin_publication import build_publish_blockers
from cupnavi_core.admin_results_repository import update_match_result_if_unchanged

def _owns(conn,account_id,tournament_id):
    return bool(conn.execute("SELECT 1 FROM tournament_members WHERE tournament_id=? AND account_id=? LIMIT 1",(int(tournament_id),int(account_id))).fetchone())
def _publication_payload(conn,tournament_id):
    t=conn.execute("SELECT * FROM tournaments WHERE id=?",(int(tournament_id),)).fetchone()
    if not t:return None
    keys=set(t.keys()); scheduled=int(conn.execute("SELECT COUNT(*) FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL",(int(tournament_id),)).fetchone()[0])
    blockers=build_publish_blockers(playoff_model_confirmed=bool(t["playoff_format"]) if "playoff_format" in keys else True,scheduled_matches=scheduled,schedule_dirty=bool(t["schedule_dirty"]) if "schedule_dirty" in keys else False,schedule_errors=())
    return {"tournament":dict(t),"scheduled_matches":scheduled,"blockers":blockers,"ready":not blockers}
def admin_publication(account_id,tournament_id):
    with get_conn() as conn:
        return _publication_payload(conn,tournament_id) if _owns(conn,account_id,tournament_id) else None
def set_publication(account_id,tournament_id,published):
    with get_conn() as conn:
        if not _owns(conn,account_id,tournament_id):return None
        state=_publication_payload(conn,tournament_id)
        if published and state["blockers"]:raise ValueError("Cupen kan inte publiceras ännu: "+" ".join(state["blockers"]))
        conn.execute("UPDATE tournaments SET is_published=? WHERE id=?",(1 if published else 0,int(tournament_id)));conn.commit();return _publication_payload(conn,tournament_id)
def admin_reporting(account_id,tournament_id):
    with get_conn() as conn:
        if not _owns(conn,account_id,tournament_id):return None
        rows=conn.execute("SELECT m.id,m.stage,m.scheduled_start,m.pitch_number,m.home_score,m.away_score,m.status,h.name AS home_team,a.name AS away_team FROM matches m JOIN teams h ON h.id=m.home_team_id JOIN teams a ON a.id=m.away_team_id WHERE m.tournament_id=? ORDER BY COALESCE(m.scheduled_start,''),m.id",(int(tournament_id),)).fetchall();return {"matches":[dict(r) for r in rows]}
def save_result(account_id,tournament_id,match_id,home_score,away_score,expected_home,expected_away):
    if home_score<0 or away_score<0:raise ValueError("Resultat kan inte vara negativa")
    with get_conn() as conn:
        if not _owns(conn,account_id,tournament_id):return None
        if not conn.execute("SELECT 1 FROM matches WHERE id=? AND tournament_id=?",(int(match_id),int(tournament_id))).fetchone():return None
        if not update_match_result_if_unchanged(conn,int(match_id),int(home_score),int(away_score),expected_home,expected_away):raise RuntimeError("Resultatet har ändrats av någon annan. Ladda om innan du sparar igen.")
        conn.execute("UPDATE matches SET status='played' WHERE id=?",(int(match_id),));conn.commit();return dict(conn.execute("SELECT id,home_score,away_score,status FROM matches WHERE id=?",(int(match_id),)).fetchone())
