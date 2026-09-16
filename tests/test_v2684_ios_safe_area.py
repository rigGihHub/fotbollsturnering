from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAYOUT = (ROOT / "frontend-next/src/app/layout.tsx").read_text()
STYLES = (ROOT / "frontend-next/src/app/ios-safe-area-v2684.css").read_text()


def test_mobile_viewport_uses_device_width_and_safe_area():
    assert 'width: "device-width"' in LAYOUT
    assert "initialScale: 1" in LAYOUT
    assert 'viewportFit: "cover"' in LAYOUT
    assert 'import "./ios-safe-area-v2684.css"' in LAYOUT


def test_ios_navigation_stays_outside_system_chrome():
    assert ".page-shell--matchday .edition-nav--desktop" in STYLES
    assert "top:env(safe-area-inset-top)!important" in STYLES
    assert "bottom:max(6px,env(safe-area-inset-bottom))!important" in STYLES
    assert "padding-bottom:0!important" in STYLES
    assert "min-height:48px!important" in STYLES
