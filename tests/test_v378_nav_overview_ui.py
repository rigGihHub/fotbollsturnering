from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
STYLE = (ROOT / "cupnavi_core" / "style_system.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_release_version():
    assert VERSION == "2026.09.03-423-PUBLIC-INFO-COLD-START"


def test_admin_navigation_has_visual_shell_and_icon_labels():
    assert 'class="cn-admin-nav-shell"' in APP
    assert '"Översikt": "⌂ Översikt"' in APP
    assert '"Deltagare": "◎ Deltagare"' in APP
    assert '"Matcher": "▦ Matcher"' in APP
    assert '"Organisation": "◇ Organisation"' in APP
    assert 'st.segmented_control(\n    "Adminområde"' in APP


def test_overview_uses_modern_header_and_next_step_card():
    block = APP[APP.index('elif admin_page == "Adminöversikt":'):APP.index('if admin_page == "Cupinställningar":')]
    assert 'class="cn-admin-overview-head"' in block
    assert 'class="cn-overview-next"' in block
    assert 'Rekommenderat nästa steg' in block
    assert 'key=f"dashboard_next_step_{tid}"' in block


def test_first_run_has_compact_visual_five_step_path():
    block = APP[APP.index('elif admin_page == "Adminöversikt":'):APP.index('if admin_page == "Cupinställningar":')]
    assert 'class="cn-first-run-hero"' in block
    assert 'class="cn-first-run-steps"' in block
    assert "1 · Lägg till lag" in block
    assert "5 · Publicera" in block
    assert 'key=f"v349_first_team_{tid}"' in block


def test_attention_remains_but_duplicate_journey_is_removed():
    block = APP[APP.index('elif admin_page == "Adminöversikt":'):APP.index('if admin_page == "Cupinställningar":')]
    assert 'class="cn-overview-attention-row' in block
    assert "cn-overview-journey" not in block
    assert "flow_items = [" not in block


def test_sidebar_and_overview_styles_are_mobile_aware():
    for marker in (
        ".cn-admin-nav-shell{",
        ".cn-admin-overview-head{",
        ".cn-overview-next{",
        ".cn-overview-attention-row{",
        ".cn-first-run-hero{",
    ):
        assert marker in STYLE
    assert 'background:#f1f5f2!important' in STYLE
    assert "/* v385 — Logical flow + no-scroll public primary navigation */" in STYLE
