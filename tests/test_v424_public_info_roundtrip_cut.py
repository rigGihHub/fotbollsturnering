from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "cupnavi_core" / "public_workspace_view.py").read_text(encoding="utf-8")
INFO = (ROOT / "cupnavi_core" / "public_info_view.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_v424_release_and_combined_info_query():
    assert VERSION == "2026.09.03-427-TRAVEL-RULES-FLOW"
    assert "SELECT sr.*" in APP
    assert "AS _total_matches" in APP
    assert "AS _open_matches" in APP
    assert "info_rules=info_rules" in APP


def test_v424_workspace_does_not_preload_completion_separately():
    info_branch = WORKSPACE.split('if public_page == "Info":', 1)[1].split("# Icke-kritisk analytics", 1)[0]
    assert "public_match_completion_db_snapshot(tournament_id)" not in info_branch
    assert "match_completion=None" in info_branch


def test_v424_info_view_accepts_prefetched_rules():
    assert "info_rules=None" in INFO
    assert "if info_rules is None:" in INFO
