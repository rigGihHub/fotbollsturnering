from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
WORKSPACE=(ROOT/"cupnavi_core"/"public_workspace_view.py").read_text(encoding="utf-8")
PUBLIC_NAV=(ROOT/"cupnavi_core/public_navigation_view.py").read_text(encoding="utf-8")
LOGIC=(ROOT/"cupnavi_core/public_view_logic.py").read_text(encoding="utf-8")
VERSION=(ROOT/"VERSION.txt").read_text(encoding="utf-8").strip()

def test_release_v201():
    assert VERSION == "2026.09.03-424-PUBLIC-INFO-ROUNDTRIP-CUT"
    assert "release_ui_label(APP_BUILD_VERSION)" in APP

def test_public_view_consumes_extracted_logic():
    assert "from cupnavi_core.public_view_logic import" in APP
    assert "resolve_public_page(" in WORKSPACE
    assert "public_navigation_specs()" in WORKSPACE
    assert "st.segmented_control(" in WORKSPACE
    assert "for page_value, section, desktop_label, mobile_label in navigation_specs" in PUBLIC_NAV
    assert "&section={quote(str(section))}" in PUBLIC_NAV

def test_logic_module_is_streamlit_free():
    assert "import streamlit" not in LOGIC
    assert "sqlite" not in LOGIC.lower()
