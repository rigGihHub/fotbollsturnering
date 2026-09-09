from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "cupnavi_core" / "public_workspace_view.py").read_text(encoding="utf-8")
MATCHES = (ROOT / "cupnavi_core" / "public_matches_view.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_v532_version_and_snapshot_support_server_limit():
    assert VERSION == "2026.09.08-532-PUBLIC-SERVER-FIRST-BATCH"
    assert "match_limit=None" in APP
    assert "COUNT(*) OVER() AS match_total" in APP
    assert "_cupnavi_public_core_v532_" in APP


def test_v532_fast_path_is_future_cup_only_and_keeps_explicit_routes_complete():
    assert "_future_cup" in WORKSPACE
    assert "_cup_start_date > datetime.now().date()" in WORKSPACE
    assert "requested_team_id is None" in WORKSPACE
    assert "requested_pitch_no is None" in WORKSPACE
    assert "requested_match_id is None" in WORKSPACE
    assert "not _active_public_search" in WORKSPACE
    assert "not _showing_highlights" in WORKSPACE
    assert "match_limit=_public_match_limit" in WORKSPACE


def test_v532_server_batch_preserves_real_total_and_load_more():
    assert "published_match_total=_published_match_total" in WORKSPACE
    assert "published_matches_complete=_published_matches_complete" in WORKSPACE
    assert "if published_matches_complete:" in MATCHES
    assert "total_filtered_matches = max(visible_match_count, int(published_match_total or 0))" in MATCHES
    assert "total_matches=max(len(published_matches), int(published_match_total or 0))" in MATCHES
