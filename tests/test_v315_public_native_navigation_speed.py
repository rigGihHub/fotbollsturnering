from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = (ROOT / "cupnavi_core" / "public_workspace_view.py").read_text(encoding="utf-8")
STYLE = (ROOT / "cupnavi_core" / "style_system.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_v315_version_is_canonical():
    assert VERSION == "2026.08.31-349-BEGINNER-FIRST-RUN"


def test_primary_navigation_uses_native_streamlit_widget_not_href_builder():
    shell = WORKSPACE[WORKSPACE.index("if not screen_mode:"):WORKSPACE.index("_public_core = public_core_snapshot")]
    assert "st.segmented_control(" in shell
    assert "build_public_navigation_html(" not in shell
    assert "on_change=_sync_public_primary_navigation" in shell


def test_native_navigation_renders_before_core_database_snapshot():
    nav = WORKSPACE.index("st.segmented_control(", WORKSPACE.index("if not screen_mode:"))
    core = WORKSPACE.index("_public_core = public_core_snapshot(")
    assert nav < core


def test_native_navigation_keeps_canonical_section_url_synced():
    assert 'st.query_params["section"] = section' in WORKSPACE
    assert 'nav_sections = {spec[0]: spec[1] for spec in nav_specs}' in WORKSPACE


def test_native_navigation_retains_sticky_five_column_shell():
    assert '[class*="st-key-cn_public_primary_nav_shell_"]' in STYLE
    assert 'position:sticky !important;top:0 !important;z-index:999995 !important' in STYLE
    assert 'grid-template-columns:repeat(5,minmax(0,1fr)) !important' in STYLE
    assert 'background:#1f6f4a !important' in STYLE
