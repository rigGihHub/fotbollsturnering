from pathlib import Path

from cupnavi_core.public_match_repository import fetch_public_match_events

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VIEW = (ROOT / "cupnavi_core" / "public_matches_view.py").read_text(encoding="utf-8")
REPOSITORY = (ROOT / "cupnavi_core" / "public_match_repository.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
WORKSPACE = (ROOT / "cupnavi_core" / "public_workspace_view.py").read_text(encoding="utf-8")


class Cursor:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows


class Con:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def execute(self, sql, params):
        self.calls.append((sql, params))
        return Cursor(self.rows)


def test_release_and_public_matches_fragment_are_extracted():
    assert VERSION == "2026.08.31-349-BEGINNER-FIRST-RUN"
    assert "from cupnavi_core.public_matches_view import render_public_matches_fragment" in APP
    assert "render_public_matches_fragment_module(" in WORKSPACE
    assert 'f"Visa {next_batch_size} fler matcher"' not in APP
    assert 'f"Visa {next_batch_size} fler matcher"' in VIEW
    assert "_cupnavi_public_matches_perf_history" in VIEW


def test_public_matches_view_has_no_direct_database_access():
    assert "with db()" not in VIEW
    assert "SELECT s.match_id" not in VIEW
    assert "load_match_events(" in VIEW
    assert "fetch_public_match_events" in REPOSITORY


def test_event_repository_groups_rows_and_uses_one_query():
    rows = [
        {"match_id": 11, "player_name": "A", "team_id": 1, "team_name": "X", "goals": 1, "red_cards": 0},
        {"match_id": 11, "player_name": "B", "team_id": 1, "team_name": "X", "goals": 0, "red_cards": 1},
        {"match_id": 12, "player_name": "C", "team_id": 2, "team_name": "Y", "goals": 2, "red_cards": 0},
    ]
    con = Con(rows)
    result = fetch_public_match_events(con, [11, 12])
    assert len(con.calls) == 1
    assert con.calls[0][1] == (11, 12)
    assert [row["player_name"] for row in result[11]] == ["A", "B"]
    assert [row["player_name"] for row in result[12]] == ["C"]


def test_event_repository_skips_empty_input_without_query():
    con = Con([])
    assert fetch_public_match_events(con, []) == {}
    assert con.calls == []


def test_app_keeps_outer_fragment_boundary_and_db_timing_service():
    block = WORKSPACE[WORKSPACE.index('if public_page == "Matcher":'):WORKSPACE.index('if public_page == "Tabeller":')]
    assert "@st.fragment\ndef render_public_view" in APP
    assert "render_public_matches_fragment_module(" in block
    db_block = APP[APP.index("def public_match_events_db_snapshot("):APP.index("def render_public_share_control")]
    assert "fetch_public_match_events" in db_block
    assert "_record_db_call(started)" in db_block
