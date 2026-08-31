from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "cupnavi_core/public_workspace_view.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_release_version():
    assert VERSION == "2026.08.31-348-GUIDED-CUP-SETUP"


def test_public_snapshot_can_skip_match_query_and_cache_modes_separately():
    block = APP[APP.index("def public_core_snapshot"):APP.index("def run_many")]
    assert "def public_core_snapshot(tournament_id, *, include_matches=True):" in block
    assert "bool(include_matches)" in block
    assert "if include_matches:" in block
    assert "matches=[]" in block


def test_public_team_snapshot_uses_compact_public_projection():
    block = APP[APP.index("def public_core_snapshot"):APP.index("def run_many")]
    assert "SELECT * FROM teams" not in block
    for field in ("id,name,group_id,age_class", "primary_color,secondary_color", "home_pattern,home_color_2,away_pattern,away_color_2"):
        assert field in block


def test_workspace_skips_matches_for_stats_and_playoffs_without_followed_team():
    assert 'public_page in {"Matcher", "Info"}' in WORKSPACE
    assert 'requested_team_id is not None' in WORKSPACE
    assert 'public_page == "Tabeller"' in WORKSPACE
    assert 'enable_final_ranking' in WORKSPACE
    assert 'include_matches=_needs_public_matches' in WORKSPACE
