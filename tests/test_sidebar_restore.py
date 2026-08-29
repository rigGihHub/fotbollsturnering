from pathlib import Path

def test_collapsed_sidebar_control_is_forced_visible():
    text = Path("cupnavi_core/style_system.py").read_text(encoding="utf-8")
    assert '[data-testid="collapsedControl"]' in text
    assert '[data-testid="stSidebarCollapsedControl"]' in text
    assert "visibility:visible !important;" in text
    assert "opacity:1 !important;" in text

def test_collapsed_sidebar_control_stays_above_content():
    text = Path("cupnavi_core/style_system.py").read_text(encoding="utf-8")
    assert "position:fixed !important;" in text
    assert "z-index:1000000 !important;" in text
    assert "pointer-events:auto !important;" in text

def test_mobile_restore_button_has_large_touch_target():
    text = Path("cupnavi_core/style_system.py").read_text(encoding="utf-8")
    assert "min-width:46px !important;" in text
    assert "min-height:46px !important;" in text
