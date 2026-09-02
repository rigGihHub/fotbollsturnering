from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()

def test_v341_version_markers():
    assert VERSION == "2026.09.02-390-PUBLIC-SHARE-TOPLIST-UX"
    assert f'APP_BUILD_VERSION = "{VERSION}"' in APP
    assert f'APP_VERSION = "{VERSION}"' in (ROOT / "cupnavi_core/version.py").read_text(encoding="utf-8")

def test_mer_no_longer_exposes_help_validation_and_recovery_globally():
    nav = APP[APP.index("ADMIN_NAV_GROUPS = ["):APP.index("ADMIN_NAV = [")]
    assert '("Kontroller", tr("Kontroller"))' not in nav
    assert '("Problem & lösningar", "Problem")' not in nav
    assert '("Instruktioner", "Guide")' not in nav
    assert '("Cupverktyg", "Cupverktyg")' not in nav
    assert '("Sponsorer", tr("Sponsorer"))' not in nav
    assert '("Mer", [])' in nav

def test_hidden_admin_tools_remain_reachable_and_owned_contextually():
    assert 'if page in {"Kontroller", "Problem & lösningar", "Instruktioner"}:' in APP
    assert 'admin_page == "Kontroller"' in APP
    assert 'admin_page == "Problem & lösningar"' in APP
    assert 'admin_page == "Instruktioner"' in APP

def test_schedule_owns_control_and_recovery_entry_points():
    assert 'with st.expander("Kontroll & felsökning", expanded=False):' in APP
    assert '"Kontrollera inför publicering"' in APP
    assert 'args=("Kontroller",)' in APP
    assert '"Felsök schemaproblem"' in APP
    assert 'args=("Problem & lösningar",)' in APP

def test_overview_owns_optional_guide_entry_point():
    assert '"Öppna steg-för-steg-guide"' in APP
    assert 'args=("Instruktioner",)' in APP
