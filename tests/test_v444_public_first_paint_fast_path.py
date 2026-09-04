from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v444_release_version():
    assert (ROOT / "VERSION.txt").read_text().strip() == "2026.09.04-449-MOBILE-PLAYOFF-ACTION"


def test_match_events_are_lazy_on_first_paint():
    source = (ROOT / "cupnavi_core/public_matches_view.py").read_text(encoding="utf-8")
    assert '"⚽ Visa målskyttar och kort"' in source
    assert "if show_match_events and visible_played_match_ids" in source
    assert "show_match_events = bool(requested_match_id) or st.toggle(" in source


def test_public_scorer_query_does_not_count_visitors():
    source = (ROOT / "cupnavi_core/public_match_repository.py").read_text(encoding="utf-8")
    start = source.index("def fetch_public_scorer_leader")
    end = source.index("def fetch_public_match_overview", start)
    block = source[start:end]
    assert "visitor_sessions" not in block
    assert "HAVING SUM(s.goals)>0" in block
    assert "LIMIT 1" in block


def test_matches_use_scorer_only_snapshot():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    workspace = (ROOT / "cupnavi_core/public_workspace_view.py").read_text(encoding="utf-8")
    assert "def public_scorer_leader_db_snapshot" in app
    assert "public_scorer_leader_db_snapshot=public_scorer_leader_db_snapshot" in app
    assert "load_overview=public_scorer_leader_db_snapshot" in workspace
