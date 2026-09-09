from pathlib import Path

MATCHES = Path("cupnavi_core/public_matches_view.py").read_text()
APP = Path("app.py").read_text()


def test_scorer_roundtrip_is_not_on_first_paint_path():
    first_paint = MATCHES[MATCHES.index("# v529: keep scorer/highlight work completely off the first-paint path."):MATCHES.index("requested_match_view =")]
    assert "load_overview(" not in first_paint
    assert 'highlights_html=""' in first_paint


def test_highlights_are_opt_in_below_match_cards():
    cards_pos = MATCHES.index("render_match_cards(")
    toggle_pos = MATCHES.index('tr("Visa turneringshöjdpunkter")')
    overview_pos = MATCHES.index("overview = load_overview(tournament_id)")
    assert cards_pos < toggle_pos < overview_pos
    assert 'value=False' in MATCHES[MATCHES.index('tr("Visa turneringshöjdpunkter")'):]


def test_v529_version_is_exposed():
    version = "2026.09.07-529-PUBLIC-MATCH-LIST-FIRST"
    assert version in APP
    assert Path("VERSION.txt").read_text().strip() == version
