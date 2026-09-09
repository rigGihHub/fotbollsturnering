from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text()
PREVIEW = (ROOT / "cupnavi_core" / "admin_publish_preview.py").read_text()
STYLE = (ROOT / "cupnavi_core" / "style_system.py").read_text()
VERSION = (ROOT / "cupnavi_core" / "version.py").read_text()


def test_v571_release_and_final_design_layer_are_wired():
    assert "2026.09.09-571-DESIGN-SYSTEM-2" in APP
    assert "2026.09.09-571-DESIGN-SYSTEM-2" in VERSION
    assert "inject_v571_design_system_2 as _inject_v571_design_system_2_impl" in APP
    assert APP.rindex("inject_v198_visual_system()") < APP.rindex("inject_v571_design_system_2()")


def test_v571_has_canonical_tokens_and_primary_secondary_hierarchy():
    assert "CUPNAVI DESIGN SYSTEM 2.0 · v571" in STYLE
    for token in ("--cn2-brand", "--cn2-bg", "--cn2-surface", "--cn2-border", "--cn2-touch"):
        assert token in STYLE
    assert 'button[kind="primary"]' in STYLE
    assert 'button[kind="secondary"]' in STYLE
    assert "Primary is reserved for the next action" in STYLE


def test_v571_unifies_forms_cards_status_navigation_and_empty_states():
    for selector in (
        '[data-testid="stWidgetLabel"]',
        '[data-testid="stTextInput"] input',
        '[data-testid="stVerticalBlockBorderWrapper"]',
        '[data-testid="stAlert"]',
        '[data-testid="stTabs"]',
        '[data-testid="stButtonGroup"]',
        '.cn-empty-state',
        '[data-testid="stDataFrame"]',
        '.cn-section-head',
    ):
        assert selector in STYLE


def test_v571_mobile_and_accessibility_contracts():
    assert "--cn2-touch:46px" in STYLE
    assert "focus-visible" in STYLE
    assert "prefers-reduced-motion:reduce" in STYLE
    assert 'button[role="tab"]{white-space:nowrap' in STYLE


def test_v570_preview_contract_is_retained():
    assert "render_public_preview" in APP or "render_publish_preview" in APP
    assert "Publikt innehåll" in PREVIEW
