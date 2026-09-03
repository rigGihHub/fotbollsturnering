from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
STYLE=(ROOT/"cupnavi_core/style_system.py").read_text(encoding="utf-8")
APP=(ROOT/"app.py").read_text(encoding="utf-8")
VERSION=(ROOT/"VERSION.txt").read_text().strip()

def test_release_version():
    assert VERSION=="2026.09.03-423-PUBLIC-INFO-COLD-START"

def test_global_typography_has_final_authority():
    assert "/* v383 — Global polish authority */" in STYLE
    assert ".stApp h1,.stApp h2,.stApp h3,.stApp h4{" in STYLE
    assert ".stApp h1{font-size:1.78rem!important" in STYLE
    assert "[data-testid=\"stCaptionContainer\"]" in STYLE

def test_buttons_share_one_control_height():
    assert '[data-testid="stButton"] button,' in STYLE
    assert "min-height:44px!important" in STYLE
    assert "Override older broad mobile rules that made every column button 64px tall." in STYLE

def test_forms_expanders_and_alerts_are_restrained():
    assert '[data-testid="stForm"]{' in STYLE
    assert '[data-testid="stExpander"]{' in STYLE
    assert '[data-testid="stAlert"]{' in STYLE
    assert "box-shadow:none!important" in STYLE

def test_empty_state_has_consistent_visual_language():
    assert ".cn-empty-state{" in STYLE
    assert ".cn-empty-state .icon{" in STYLE
    assert ".cn-empty-state b{" in STYLE
    assert ".cn-empty-state p{" in STYLE
    assert "def render_empty_state" in APP

def test_section_headers_and_data_containers_are_normalized():
    assert ".cn-section-head,.cn-info-section-title{" in STYLE
    assert '[data-testid="stDataFrame"],[data-testid="stDataEditor"]{' in STYLE
    assert '[data-testid="stWidgetLabel"] p{' in STYLE

def test_mobile_polish_keeps_44px_controls_and_removes_card_shadow():
    assert "@media(max-width:768px)" in STYLE
    assert "div[data-testid=\"stHorizontalBlock\"] > div[data-testid=\"stColumn\"] button{" in STYLE
    assert ".cn-workspace-head,.cn-admin-overview-head,.cn-info-guide-head{" in STYLE
