from pathlib import Path

APP = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")

def test_calendar_is_fully_light_and_weekdays_readable():
    assert "CUPNAVI CALENDAR FINAL OVERRIDE" in APP
    assert '[data-baseweb="calendar"] *' in APP
    assert '[data-baseweb="calendar"] [role="columnheader"]' in APP
    assert 'background:#ffffff !important;' in APP
    assert 'color:#334155 !important;' in APP
    assert 'background:#166534 !important;' in APP

def test_team_page_does_not_duplicate_class_crud():
    start = APP.index('if admin_page == "Lag":')
    end = APP.index('if admin_page == "Grupper":', start)
    block = APP[start:end]
    assert '"Hantera tävlingsklasser"' in block
    assert 'key=f"manage_add_class_{tid}"' not in block
    assert 'key=f"remove_class_' not in block
    assert 'with st.expander("Fler lagverktyg", expanded=False)' in block

def test_secondary_text_has_explicit_contrast():
    assert '[data-testid="stCaptionContainer"]' in APP
    assert 'color:#64748b !important;' in APP
    assert '[data-testid="stWidgetLabel"] p' in APP
