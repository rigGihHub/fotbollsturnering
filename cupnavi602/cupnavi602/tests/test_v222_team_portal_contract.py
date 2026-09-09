
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
VIEW=(ROOT/"cupnavi_core/team_portal_view.py").read_text(encoding="utf-8")

def test_team_and_admin_roster_saves_use_optimistic_helper():
    assert "def _save_match_roster_if_unchanged(" in APP
    assert "save_match_roster_if_unchanged=_save_match_roster_if_unchanged" in APP
    assert VIEW.count("deps.save_match_roster_if_unchanged(") == 2

def test_roster_conflict_feedback_is_user_visible():
    assert "Matchtruppen ändrades av någon annan och skrevs inte över." in VIEW

def test_roster_writer_validates_player_team_membership():
    start=APP.index("def _save_match_roster_if_unchanged")
    end=APP.index("def render_team_portal",start)
    block=APP[start:end]
    assert "SELECT id FROM players WHERE team_id=? AND id IN" in block
    assert 'return False, "invalid_players"' in block
