from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
STYLE = (ROOT / "cupnavi_core" / "style_system.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_v564_release_sync_and_admin_dashboard_return():
    assert VERSION == "2026.09.08-564-ADMIN-UX-EXPERT-POLISH"
    assert '2026.09.08-564-ADMIN-UX-EXPERT-POLISH' in APP
    assert 'def _back_to_my_cups()' in APP
    assert '"← Mina cuper"' in APP


def test_v564_secondary_tools_do_not_compete_with_numbered_flow():
    assert 'st.columns(2)' in APP
    assert '"🔐 Åtkomst & koder"' in APP
    assert 'type="secondary"' in APP
    assert 'Alla nio huvudsteg är alltid åtkomliga.' not in APP


def test_v564_access_center_has_task_tabs():
    assert 'st.header("Åtkomst & koder")' in APP
    assert '"👥 Administratörer", "🔐 Koder", "👤 Min profil"' in APP
    assert 'with _access_people_tab:' in APP
    assert 'with _access_codes_tab:' in APP
    assert 'with _access_profile_tab:' in APP


def test_v564_current_step_gets_compact_visual_hierarchy():
    assert "cn-admin-current-step" in APP
    assert ".cn-admin-current-step" in STYLE
    assert "Cupflöde" in APP
