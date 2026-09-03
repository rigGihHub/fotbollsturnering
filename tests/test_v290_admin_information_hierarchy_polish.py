from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_release_version():
    assert VERSION == "2026.09.03-423-PUBLIC-INFO-COLD-START"
    assert VERSION in APP


def test_duplicate_admin_chrome_removed():
    assert "st.sidebar.caption(f\"{tr('Visningsläge')}: {tr(view_mode)}\")" not in APP
    assert "<div class='cn-admin-section-label'>" not in APP
    assert "<div class='cn-admin-nav-group-title'>" not in APP


def test_overview_does_not_get_duplicate_global_next_step_card():
    assert 'admin_page not in (_recommended_page, "Adminöversikt")' in APP
    assert 'f"Fortsätt → {_recommended_label}"' in APP


def test_primary_admin_navigation_and_search_remain_available():
    assert "ADMIN_NAV_GROUPS = [" in APP
    assert 'with st.expander("Sök i cupen", expanded=False):' in APP
    assert 'with st.expander("Fler verktyg", expanded=_advanced_active):' in APP
