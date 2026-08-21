from pathlib import Path

def app_text():
    return Path("app.py").read_text(encoding="utf-8")

def test_admin_navigation_is_grouped():
    text=app_text()
    assert "ADMIN_NAV_GROUPS = [" in text
    for label in ("Kom igång","Planering","Under cupen","Besökare och övrigt"):
        assert label in text

def test_current_page_and_status_are_visible():
    text=app_text()
    assert "cn-current-admin-page" in text
    assert "cn-admin-status-strip" in text
    assert "Aktuell sida" in text

def test_public_share_is_compact():
    text=app_text()
    start=text.index("def render_public_view(")
    block=text[start:start+9000]
    assert "public_share_open_" in block
    assert "if share_is_open:" in block
    assert 'render_share_panel(tournament_id, tournament["name"])' in block

def test_touch_and_keyboard_accessibility():
    text=app_text()
    assert "min-height:44px" in text
    assert "focus-visible" in text
