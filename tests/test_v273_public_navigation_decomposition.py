from pathlib import Path

from cupnavi_core.public_navigation_view import build_public_navigation_html
from cupnavi_core.public_view_logic import public_navigation_specs


ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
WORKSPACE = (ROOT / "cupnavi_core" / "public_workspace_view.py").read_text(encoding="utf-8")


def test_release_version_v273():
    assert VERSION == "2026.08.31-349-BEGINNER-FIRST-RUN"


def test_navigation_builder_keeps_single_responsive_nav_and_active_page():
    rendered = build_public_navigation_html(
        public_navigation_specs(),
        current_page="Matcher",
        public_slug="test-cup",
        requested_team_id=42,
        translate=lambda text: f"T:{text}",
    )
    assert rendered.count("<nav ") == 1
    assert rendered.count("<a role='button'") == 5
    assert "class='active' href='?cup=test-cup&amp;section=matches&amp;team=42'" in rendered
    assert "cn-nav-desktop" in rendered
    assert "cn-nav-mobile" in rendered
    assert "Cupinfo" in rendered
    assert "T:Schema &amp; resultat" in rendered


def test_navigation_builder_escapes_labels_and_encodes_slug():
    specs = (("Matcher", "matches", "A < B", 'M & "N"'),)
    rendered = build_public_navigation_html(
        specs,
        current_page="Matcher",
        public_slug="cup / å",
        requested_team_id="not-an-id",
        translate=lambda value: value,
    )
    assert "cup%20/%20%C3%A5" in rendered
    assert "A &lt; B" in rendered
    assert "M &amp; &quot;N&quot;" in rendered
    assert "&amp;team=" not in rendered


def test_navigation_builder_remains_framework_agnostic_and_native_workspace_owns_interaction():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    module = (ROOT / "cupnavi_core" / "public_navigation_view.py").read_text(encoding="utf-8")
    assert "nav_links = []" not in app
    assert "st.segmented_control(" in WORKSPACE
    assert "build_public_navigation_html(" not in WORKSPACE[WORKSPACE.index("if not screen_mode:"):WORKSPACE.index("_public_core = public_core_snapshot")]
    assert "import streamlit" not in module.lower()
    assert "sqlite" not in module.lower()
    assert ".execute(" not in module
