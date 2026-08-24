from pathlib import Path

def app_text():
    return Path("app.py").read_text(encoding="utf-8")

def test_admin_navigation_is_grouped():
    text=app_text()
    assert "ADMIN_NAV_GROUPS = [" in text
    for label in ("Översikt","Deltagare","Matcher","Organisation","Kommunikation"):
        assert label in text

def test_current_page_and_status_are_visible():
    text=app_text()
    assert "cn-current-admin-page" in text
    assert "cn-admin-status-strip" in text
    assert "Aktuell sida" in text

def test_public_share_is_compact():
    text=app_text()
    # Sharing is now a single global, fixed entry point beside the logo. The
    # integrated panel itself is rendered inside the public view only when
    # share=1 is requested, so the test verifies behaviour rather than the old
    # implementation detail that all share markup lived inside render_public_view().
    assert "cn-fixed-share" in text
    assert "share=1#cn-share-section" in text
    start=text.index("def render_public_view(")
    block=text[start:start+30000]
    assert "if share_is_open:" in block
    assert "cn-integrated-share" in block
    assert "public_share_open_" not in text

def test_touch_and_keyboard_accessibility():
    text=app_text()
    assert "min-height:44px" in text
    assert "focus-visible" in text
