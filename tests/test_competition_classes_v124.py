from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
SETUP = (ROOT / "cupnavi_core" / "initial_setup_view.py").read_text(encoding="utf-8")

def test_competition_class_language_and_hierarchy_are_visible():
    assert "Tävlingsklasser" in APP + SETUP
    assert "Planerade lag" in SETUP
    assert "competition_class_label" in APP
    lag_start = APP.index('if admin_page == "Lag":')
    lag_end = APP.index('if admin_page == "Grupper":', lag_start)
    lag = APP[lag_start:lag_end]
    assert 'with st.expander("Tävlingsklasser", expanded=False)' in lag
    assert '"Hantera tävlingsklasser"' in lag
