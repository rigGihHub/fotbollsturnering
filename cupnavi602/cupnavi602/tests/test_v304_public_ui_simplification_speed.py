from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATCHES = (ROOT / "cupnavi_core" / "public_matches_view.py").read_text(encoding="utf-8")
OVERVIEW = (ROOT / "cupnavi_core" / "public_match_overview.py").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "cupnavi_core" / "public_workspace_view.py").read_text(encoding="utf-8")


def test_matches_page_still_avoids_full_table_and_statistics_work():
    # v391 deliberately supersedes v304's complete removal of highlights. The
    # primary view may load one compact scorer snapshot, but it must not restore
    # the expensive full table/statistics calculations that v304 removed.
    assert "snapshot_table_bundle(" not in MATCHES
    assert "competition_highlights(" not in MATCHES
    assert "calculate_all_group_tables(" not in MATCHES
    assert 'load_overview=public_scorer_leader_db_snapshot' in WORKSPACE


def test_matches_summary_remains_compact_while_accepting_small_highlights():
    assert "team_count" in OVERVIEW
    assert "played_count" in OVERVIEW
    assert "total_matches" in OVERVIEW
    assert "total_score" in OVERVIEW
    summary = OVERVIEW[OVERVIEW.index("def build_summary_html"):]
    assert "active_visitors" not in summary
    assert "highlights_html" in summary
    assert "cn-public-summary-row" in summary
