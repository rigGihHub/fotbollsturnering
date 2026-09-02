from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")

def test_clock_is_browser_driven_without_streamlit_reruns():
    assert "def render_tournament_clock(tournament_row):" in APP
    assert "setInterval(tickCupNaviClock, 1000)" in APP
    block = APP.split("def render_tournament_clock(tournament_row):", 1)[1].split("with st.sidebar:", 1)[0]
    assert "st.rerun" not in block
    assert "run(" not in block

def test_clock_uses_tournament_timezone_and_seconds():
    assert '_row_value(tournament_row, "timezone_name", "Europe/Stockholm")' in APP
    assert "second: '2-digit'" in APP
    assert "with st.sidebar:" in APP
    assert "render_tournament_clock(tournament)" in APP
