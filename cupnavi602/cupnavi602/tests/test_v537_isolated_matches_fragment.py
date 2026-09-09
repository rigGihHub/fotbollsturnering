from pathlib import Path

APP = Path("app.py").read_text(encoding="utf-8")
WORKSPACE = Path("cupnavi_core/public_workspace_view.py").read_text(encoding="utf-8")


def test_v537_version_exposed():
    assert "2026.09.08-537-ISOLATED-MATCHES-FRAGMENT" in APP


def test_v537_matches_renderer_has_own_fragment_boundary():
    assert "@st.fragment\ndef render_public_matches_isolated_fragment(**kwargs):" in APP
    assert "return render_public_matches_fragment_module(**kwargs)" in APP


def test_v537_public_workspace_uses_isolated_matches_fragment():
    public_view = APP[APP.index("@st.fragment\ndef render_public_view"):APP.index("\ndef _reporter_save_quick_result", APP.index("@st.fragment\ndef render_public_view"))]
    assert "render_public_matches_fragment_module=render_public_matches_isolated_fragment" in public_view
    assert "render_public_matches_fragment_module=render_public_matches_fragment_module" not in public_view


def test_v537_workspace_keeps_match_page_as_child_renderer():
    assert "if public_page == \"Matcher\":" in WORKSPACE
    assert "render_public_matches_fragment_module(" in WORKSPACE
