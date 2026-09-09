from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
NAV = (ROOT / "cupnavi_core" / "planning_flow_nav.py").read_text(encoding="utf-8")


def test_shared_control_publish_route_keeps_correct_visible_step():
    assert 'if page_name == "Kontroller":' in APP
    assert 'planning_control_focus_{tid}' in APP
    assert 'step_label if step_label in {"Kontroll", "Publicera"}' in APP


def test_global_flow_suppresses_duplicate_workspace_flow():
    assert 'st.session_state[f"_global_admin_flow_rendered_{tid}"] = True' in APP
    assert 'if st.session_state.get(f"_global_admin_flow_rendered_{tid}")' in NAV
    assert 'return' in NAV


def test_control_back_button_uses_real_schema_route():
    control_start = APP.index('if admin_page == "Kontroller":')
    control_source = APP[control_start:control_start + 9000]
    assert 'args=("Skapa och publicera schema",)' in control_source
    assert 'args=("Schema",)' not in control_source


def test_revision_source_is_visible_from_overview_and_not_participant_scoped():
    assert '"🔄 Ny eller ändrad PDF / foto"' in APP
    assert 'key=f"overview_revision_source_{tid}"' in APP
    assert 'if page == "Import":\n        return "Översikt"' in APP
    assert '{"Trupper", "Önskemålscentral", "Import", "Tröj setup"}' not in APP


def test_v587_version_is_synchronized():
    version = "2026.09.09-587-FLOW-UX-EXPERT-PASS"
    assert version in APP
    assert (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip() == version
    assert version in (ROOT / "cupnavi_core" / "version.py").read_text(encoding="utf-8")
