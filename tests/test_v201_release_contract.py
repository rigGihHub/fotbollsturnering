from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
LOGIC=(ROOT/"cupnavi_core/public_view_logic.py").read_text(encoding="utf-8")
VERSION=(ROOT/"VERSION.txt").read_text(encoding="utf-8").strip()

def test_release_v201():
    assert VERSION == "2026.08.28-249-PUBLIC-MATCH-RENDER-FIX"
    assert "Version v.1.249" in APP

def test_public_view_consumes_extracted_logic():
    assert "from cupnavi_core.public_view_logic import" in APP
    assert "resolve_public_page(" in APP
    assert "public_navigation_specs()" in APP
    assert "public_section_for_page(page_value)" in APP

def test_logic_module_is_streamlit_free():
    assert "import streamlit" not in LOGIC
    assert "sqlite" not in LOGIC.lower()
