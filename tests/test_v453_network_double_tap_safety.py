from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VIEW = (ROOT / "cupnavi_core" / "match_reporter_workspace_view.py").read_text(encoding="utf-8")
PRESENTATION = (ROOT / "cupnavi_core" / "match_reporter_view.py").read_text(encoding="utf-8")
VERSION = "2026.09.07-499-DOCUMENT-TO-COMPLETE-PROPOSAL"


def test_release_version():
    assert (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip() == VERSION
    assert VERSION in APP


def test_live_goal_still_uses_two_optimistic_locks_inside_one_transaction():
    block = APP[APP.index("def _reporter_live_goal_transaction"):APP.index("def _reporter_save_event_rows")]
    assert 'con.execute("BEGIN" if CLOUD_DATABASE_ENABLED else "BEGIN IMMEDIATE")' in block
    assert "update_match_result_if_unchanged(" in block
    assert "update_player_match_stats_if_unchanged(" in block
    assert block.index("update_match_result_if_unchanged(") < block.index("update_player_match_stats_if_unchanged(")
    assert "con.rollback()" in block
    assert "con.commit()" in block


def test_stale_second_tap_is_explained_as_no_extra_write():
    assert "Ingen extra måländring sparades" in VIEW
    assert "Ingen extra ändring sparades" in VIEW
    assert "vänta på grön bekräftelse" in VIEW
    assert "Mål säkert sparat på servern" in VIEW


def test_offline_draft_shows_browser_network_state():
    assert "navigator.onLine" in PRESENTATION
    assert "window.addEventListener('online',networkStatus)" in PRESENTATION
    assert "window.addEventListener('offline',networkStatus)" in PRESENTATION
    assert "Offline – använd detta lokala utkast" in PRESENTATION


def test_offline_score_draft_autosaves_on_each_score_change():
    assert "h.addEventListener('input',()=>saveLocal())" in PRESENTATION
    assert "a.addEventListener('input',()=>saveLocal())" in PRESENTATION
    assert "Autosparat lokalt på enheten." in PRESENTATION
    assert "synkas inte automatiskt" in PRESENTATION


def test_offline_component_has_more_room_for_connection_status():
    assert "height=235" in VIEW
