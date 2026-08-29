
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
VIEW=(ROOT/"cupnavi_core/team_portal_view.py").read_text(encoding="utf-8")
REPO=(ROOT/"cupnavi_core/team_portal_repository.py").read_text(encoding="utf-8")


def _portal_source():
    return VIEW


def test_team_portal_add_uses_atomic_capacity_writer():
    portal=_portal_source()
    assert "deps.add_team_player_if_capacity(" in portal


def test_team_portal_edit_delete_use_optimistic_writers():
    portal=_portal_source()
    assert "deps.update_team_player_if_unchanged(" in portal
    assert "deps.delete_team_player_if_unchanged(" in portal
    assert "Spelaren ändrades av någon annan" in portal


def test_capacity_is_enforced_inside_insert_statement():
    start=APP.index("def _add_team_player_if_capacity")
    end=APP.index("def _update_team_player_if_unchanged",start)
    block=APP[start:end]
    assert "SELECT COUNT(*) FROM players WHERE team_id=?" in block
    assert ") < ?" in block
