from pathlib import Path
VERSION = "2026.09.07-502-GUIDED-ADMIN-FLOW"
APP = Path("app.py").read_text(encoding="utf-8")
def test_version_is_v492():
    assert Path("VERSION.txt").read_text().strip() == VERSION
    assert VERSION in APP
def test_rerun_budget_reduced():
    assert APP.count("st.rerun()") <= 86
def test_cupday_compare_uses_callback():
    i=APP.index('key=f"autopilot_compare_')
    block=APP[i-250:i+700]
    assert "on_click=_open_cupday_delay" in block
    assert "st.rerun()" not in block
def test_open_setup_uses_callback():
    i=APP.index('"Ändra cupens inställningar"')
    block=APP[i-500:i+600]
    assert "on_click=_open_current_cup_setup" in block
    assert "st.rerun()" not in block
def test_open_team_roster_uses_callback():
    i=APP.index('"Öppna lagets trupp"')
    block=APP[i-700:i+800]
    assert "on_click=_open_focused_team_roster" in block
    assert "st.rerun()" not in block
