from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEW = (ROOT / 'cupnavi_core' / 'public_matches_view.py').read_text(encoding='utf-8')
VERSION = (ROOT / 'VERSION.txt').read_text(encoding='utf-8').strip()


def test_version_and_summary_highlights_restored():
    assert VERSION.startswith('2026.09.08-541-')
    assert 'summary_highlights: dict[str, Any] = {}' in VIEW
    assert 'highlights_html=build_highlights_html(summary_highlights, tr=tr)' in VIEW


def test_top_scorer_is_automatic_again():
    assert 'overview = load_overview(tournament_id)' in VIEW
    assert 'summary_highlights["scorer"]' in VIEW
    assert 'summary_played_count > 0' in VIEW


def test_partial_server_batch_does_not_fake_team_rankings():
    assert 'if played_matches and published_matches_complete:' in VIEW
