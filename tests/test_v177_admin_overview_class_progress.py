from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
ADMIN=(ROOT/"cupnavi_core/admin_overview.py").read_text(encoding="utf-8")
R="2026.08.29-291-ADMIN-PAGE-SIMPLIFICATION"

def test_duplicate_next_button_is_suppressed():
    assert "v160_next_" not in APP
    assert "Nästa steg" in APP

def test_admin_overview_is_class_aware():
    assert "class_progress_caption(" in APP
    assert "Lag per tävlingsklass" in ADMIN
    assert "_v139_class_rows = competition_classes(tid)" in APP
    assert "planerade totalt" in APP
    assert 'with st.expander("Förberedelser i detalj", expanded=False)' in APP

def test_rules_readiness_is_data_driven():
    assert "sidebar_rules=sidebar_rules" in APP
    assert 'int(_value(rules, "minutes_per_half", 0) or 0) > 0' in ADMIN

def test_checkin_copy_matches_new_setup_model():
    assert "Lagincheckning:" not in APP[APP.index('if admin_page == "Adminöversikt":'):APP.index('if admin_page == "Cupinställningar":')]
    assert "valet gjordes när turneringen skapades" not in APP

def test_release_sync():
    assert f'APP_BUILD_VERSION = "{R}"' in APP
    assert f'APP_VERSION = "{R}"' in (ROOT/"cupnavi_core/version.py").read_text(encoding="utf-8")
    assert (ROOT/"VERSION.txt").read_text().strip()==R
