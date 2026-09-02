
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
INFO=(ROOT/"cupnavi_core/public_info_view.py").read_text(encoding="utf-8")
VERSION=(ROOT/"VERSION.txt").read_text(encoding="utf-8").strip()

def test_public_info_has_dedicated_view_module():
    assert "def render_public_info_section(" in INFO
    assert "SELECT * FROM functionaries" in INFO
    assert "SELECT * FROM offers" in INFO
    assert "SELECT * FROM sponsors" in INFO
    assert "public_feedback_" in INFO

def test_app_keeps_thin_info_adapter_inside_outer_public_fragment():
    start=APP.index("def render_public_info_section")
    end=APP.index("@st.fragment\ndef render_public_view",start)
    block=APP[start:end]
    assert "render_public_info_section_module(" in block
    assert "rate_allowed=_rate_allowed" in block
    assert len(block.splitlines()) < 30

def test_business_helpers_are_injected_not_reimplemented():
    assert "one_row=one_row" in APP
    assert "all_rows=all_rows" in APP
    assert "public_rules_html=public_rules_html" in APP
    assert "cup_summary=cup_summary" in APP
    assert "sport_profile=sport_profile" in APP

def test_release_is_v202():
    assert VERSION=="2026.09.02-390-PUBLIC-SHARE-TOPLIST-UX"
    assert "release_ui_label(APP_BUILD_VERSION)" in APP
