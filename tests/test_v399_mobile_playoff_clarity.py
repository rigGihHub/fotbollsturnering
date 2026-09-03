from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION.txt").read_text().strip()
PRESENTATION = (ROOT / "cupnavi_core" / "public_presentation_view.py").read_text()

def test_v399_version():
    assert VERSION == "2026.09.03-424-PUBLIC-INFO-ROUNDTRIP-CUT"

def test_mobile_playoff_marks_winner_and_decider():
    assert "team{' winner' if home_winner else ''}" in PRESENTATION
    assert "content:'Vinnare'" in PRESENTATION
    assert "class='decider'" in PRESENTATION
    assert 'Straffar {match_row' in PRESENTATION
    assert 'Avgjord genom lottning' in PRESENTATION

def test_bronze_is_outside_desktop_scroll_and_resolves_teams():
    scroll_close = PRESENTATION.index('</div>\n        {bronze_html}')
    assert scroll_close > PRESENTATION.index('class="classic-bracket-scroll"')
    assert 'bronze_home_team = bracket_team_by_id.get' in PRESENTATION
    assert 'bronze_away_team = bracket_team_by_id.get' in PRESENTATION
    assert "bronze_home_winner, bronze_away_winner" in PRESENTATION

def test_no_new_team_query_for_mobile_details():
    block = PRESENTATION[PRESENTATION.index('mobile_rounds = []'):PRESENTATION.index('st.markdown(', PRESENTATION.index('mobile_rounds = []'))]
    assert 'all_rows(' not in block
