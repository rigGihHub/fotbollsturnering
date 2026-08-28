from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
R="2026.08.28-270-INCREMENTAL-PUBLIC-MATCHES"

def test_duplicate_next_button_is_suppressed():
    assert "v160_next_" not in APP
    assert "Nästa steg" in APP

def test_admin_overview_is_class_aware():
    assert "Lag per tävlingsklass" in APP
    assert "_v139_class_rows = competition_classes(tid)" in APP
    assert "planerade totalt" in APP
    assert 'with st.expander("Förberedelser i detalj", expanded=False)' in APP

def test_rules_readiness_is_data_driven():
    assert "_v139_rules_ready = bool(" in APP
    assert 'int(_row_value(_v139_rules, "minutes_per_half", 0) or 0) > 0' in APP

def test_checkin_copy_matches_new_setup_model():
    assert "Lagincheckning:" not in APP[APP.index('if admin_page == "Adminöversikt":'):APP.index('if admin_page == "Cupinställningar":')]
    assert "valet gjordes när turneringen skapades" not in APP

def test_release_sync():
    assert f'APP_BUILD_VERSION = "{R}"' in APP
    assert f'APP_VERSION = "{R}"' in (ROOT/"cupnavi_core/version.py").read_text(encoding="utf-8")
    assert (ROOT/"VERSION.txt").read_text().strip()==R
