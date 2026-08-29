from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
STYLE=(ROOT/"cupnavi_core/style_system.py").read_text(encoding="utf-8")
RESULTS_VIEW=(ROOT/"cupnavi_core"/"admin_results_view.py").read_text(encoding="utf-8")

def test_admin_has_single_primary_flow():
    assert "ADMIN_PRIMARY_FLOW = [" in APP
    for page in ("Adminöversikt","Lag","Grupper","Skapa och publicera schema","Matcher och resultat","Tabeller","Slutspel"):
        assert f'("{page}",' in APP

def test_pages_explain_purpose_and_status():
    assert "ADMIN_PAGE_COPY = {" in APP
    assert "cn-flow-context" in APP
    assert "Schema behöver uppdateras" in APP
    assert 'f"Resultat {_flow_played}/{_flow_total}"' in APP

def test_recommended_next_step_is_state_driven():
    assert '_recommended_page, _recommended_label = "Lag", "Lägg till lag"' in APP
    assert '_recommended_page, _recommended_label = "Grupper", "Skapa grupper"' in APP
    assert '_recommended_page, _recommended_label = "Skapa och publicera schema"' in APP
    assert '_recommended_page, _recommended_label = "Matcher och resultat"' in APP

def test_primary_flow_has_previous_next_navigation():
    assert "v160_prev_" not in APP and "v160_next_" not in APP
    assert "Nästa steg" in APP

def test_results_page_has_progress_and_public_state():
    assert "Resultatstatus" in RESULTS_VIEW
    assert "cn-progress-track" in RESULTS_VIEW
    assert "✓ Publika resultat uppdateras automatiskt." in RESULTS_VIEW
    assert "render_admin_results_workspace(" in APP

def test_mobile_touch_targets_remain_accessible():
    assert "min-height:46px !important" in STYLE
    assert "button:focus-visible" in STYLE
