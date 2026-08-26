from pathlib import Path

APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")

def test_public_visit_is_single_upsert():
    block=APP[APP.index("def track_public_visit"):APP.index("@st.cache_data(show_spinner=False)")]
    assert "ON CONFLICT(tournament_id,session_token) DO UPDATE" in block
    assert "SELECT id,view_count FROM visitor_sessions" not in block

def test_public_matches_prejoin_referee_and_pitch():
    block=APP[APP.index("def public_core_snapshot"):APP.index("def run_many")]
    assert "LEFT JOIN referees r ON r.id=m.referee_id" in block
    assert "LEFT JOIN pitches p ON p.tournament_id=m.tournament_id" in block
    cards=APP[APP.index("def _render_public_match_cards"):APP.index("render_public_matches_fragment()", APP.index("def _render_public_match_cards"))]
    assert 'SELECT * FROM referees WHERE tournament_id=?' not in cards

def test_weather_skips_network_outside_forecast_window():
    block=APP[APP.index("def _render_public_match_cards"):APP.index("render_public_matches_fragment()", APP.index("def _render_public_match_cards"))]
    assert "weather_horizon = weather_now + timedelta(days=16)" in block
    assert "if forecastable:" in block
