
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
VERSION=(ROOT/"VERSION.txt").read_text(encoding="utf-8").strip()

def test_final_visual_system_exists():
    assert "CUPNAVI VISUAL SYSTEM v1.198" in APP
    assert "inject_v198_visual_system()" in APP

def test_required_visual_tokens_exist():
    for token in [
        "--cn98-primary:", "--cn98-bg:", "--cn98-surface:", "--cn98-border:",
        "--cn98-ink:", "--cn98-ink-2:", "--cn98-success:", "--cn98-warning:",
        "--cn98-error:", "--cn98-info:", "--cn98-control:"
    ]:
        assert token in APP

def test_responsive_accessibility_contract():
    assert "@media(max-width:1024px)" in APP
    assert "@media(max-width:768px)" in APP
    assert "@media(max-width:390px)" in APP
    assert "@media(min-width:1440px)" in APP
    assert "@media(prefers-reduced-motion:reduce)" in APP
    assert "focus-visible" in APP
    assert "--cn98-control:44px" in APP

def test_core_components_are_normalized():
    for token in [
        '[data-testid="stTextInput"] input',
        '[data-testid="stButton"] button',
        '[data-testid="stDataFrame"]',
        '[data-testid="stAlert"]',
        '[data-testid="stTabs"]',
        '.classic-bracket',
        '[data-baseweb="popover"] > div',
    ]:
        assert token in APP

def test_release_is_v198():
    assert VERSION == "2026.08.28-266-MOBILE-PUBLIC-PERFORMANCE-UX"
    assert "Version v.1.266" in APP
