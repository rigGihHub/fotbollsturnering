from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION.txt").read_text().strip()
APP = (ROOT / "app.py").read_text()
WORKSPACE = (ROOT / "cupnavi_core/public_workspace_view.py").read_text()
INFO = (ROOT / "cupnavi_core/public_info_view.py").read_text()


def test_v423_release_and_info_fast_path_contract():
    assert VERSION == "2026.09.03-423-PUBLIC-INFO-COLD-START"
    assert "def public_match_completion_db_snapshot" in APP
    assert 'or public_page in {"Matcher", "Mitt lag"}' in WORKSPACE
    assert '_needs_public_teams = public_page != "Info"' in WORKSPACE
    assert 'include_teams=_needs_public_teams' in WORKSPACE
    assert 'include_matches=True,\n                include_teams=False' in WORKSPACE
    assert 'load_published_matches=_load_info_published_matches' in WORKSPACE
    assert 'cup_is_complete = total_public_matches > 0 and open_public_matches == 0' in INFO
    assert 'if not all_public_matches and load_published_matches is not None:' in INFO
