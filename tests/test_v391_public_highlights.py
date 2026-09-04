from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATCHES = (ROOT / "cupnavi_core" / "public_matches_view.py").read_text(encoding="utf-8")
OVERVIEW = (ROOT / "cupnavi_core" / "public_match_overview.py").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "cupnavi_core" / "public_workspace_view.py").read_text(encoding="utf-8")


def test_public_matches_restores_compact_highlights_in_summary_space():
    assert 'highlights["attack"]' in MATCHES
    assert 'highlights["defence"]' in MATCHES
    assert 'highlights["scorer"]' in MATCHES
    assert 'highlights_html=highlights_html' in MATCHES
    assert 'load_overview=public_scorer_leader_db_snapshot' in WORKSPACE


def test_highlight_labels_match_requested_public_signals():
    assert "Flest gjorda mål" in OVERVIEW
    assert "Minst insläppta" in OVERVIEW
    assert "Skytteligaledare" in OVERVIEW
