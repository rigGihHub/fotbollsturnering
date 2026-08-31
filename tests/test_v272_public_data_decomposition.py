from pathlib import Path
from cupnavi_core.public_match_repository import fetch_public_match_overview

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()

class Cursor:
    def __init__(self, row): self.row = row
    def fetchone(self): return self.row
class Con:
    def __init__(self, row): self.row=row; self.calls=[]
    def execute(self, sql, params): self.calls.append((sql, params)); return Cursor(self.row)

def test_release_and_repository_boundary():
    assert VERSION == "2026.08.31-349-BEGINNER-FIRST-RUN"
    block=APP[APP.index('def public_match_overview_db_snapshot('):APP.index('def render_public_share_control')]
    assert 'fetch_public_match_overview' in block
    assert 'WITH agg AS (' not in block

def test_repository_returns_unique_leaders_and_one_query():
    row={"visitor_count":2,"scorer_player":"A","scorer_team":"X","scorer_goals":4,"scorer_assists":1,
         "assist_player":"B","assist_team":"Y","assist_goals":1,"assist_assists":5}
    con=Con(row)
    out=fetch_public_match_overview(con,tournament_id=7,cutoff="2026-08-28T20:00:00",session_token="me")
    assert len(con.calls)==1
    assert out["visitor_count"]==2
    assert [x["player_name"] for x in out["leader_rows"]]==["A","B"]
