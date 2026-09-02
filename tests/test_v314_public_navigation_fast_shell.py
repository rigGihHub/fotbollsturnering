from pathlib import Path

WORKSPACE = Path("cupnavi_core/public_workspace_view.py").read_text()
VERSION = Path("VERSION.txt").read_text().strip()


def test_v314_version():
    assert VERSION == "2026.09.02-390-PUBLIC-SHARE-TOPLIST-UX"


def test_navigation_is_rendered_before_public_core_snapshot_on_normal_public_path():
    navigation = WORKSPACE.index("st.segmented_control(", WORKSPACE.index("if not screen_mode:"))
    core = WORKSPACE.index("_public_core = public_core_snapshot(")
    assert navigation < core


def test_team_follow_is_no_longer_before_navigation():
    navigation = WORKSPACE.index("st.segmented_control(", WORKSPACE.index("if not screen_mode:"))
    team_follow = WORKSPACE.index("render_public_team_follow(")
    assert navigation < team_follow


def test_screen_mode_still_returns_without_normal_public_content():
    screen_branch = WORKSPACE[WORKSPACE.index("if screen_mode:"):WORKSPACE.index("# Only now validate")]
    assert "render_public_screen_mode(" in screen_branch
    assert "return" in screen_branch
