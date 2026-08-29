from pathlib import Path

def test_tab_navigation_is_sticky():
    text=Path("cupnavi_core/style_system.py").read_text(encoding="utf-8")
    assert "position:sticky !important;" in text
    assert "z-index:999 !important;" in text
    assert 'div[data-baseweb="tab-list"]' in text

def test_mobile_tabs_remain_horizontally_scrollable():
    text=Path("cupnavi_core/style_system.py").read_text(encoding="utf-8")
    assert "overflow-x:auto !important;" in text
    assert "-webkit-overflow-scrolling:touch !important;" in text
