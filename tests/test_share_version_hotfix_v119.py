from pathlib import Path


def app_text():
    return Path("app.py").read_text(encoding="utf-8")


def test_fixed_share_is_same_page_native_control():
    text = app_text()
    assert ".cn-share-toggle-anchor + div {" in text
    assert 'cn_share_visible_' in text
    assert 'cn_share_button_' in text
    assert 'cn-share-panel-anchor' in text
    assert 'popovertarget=' not in text
    assert "popover='auto'" not in text

def test_only_short_version_is_used_for_users():
    text = app_text()
    assert 'st.sidebar.caption(f"CupNavi version {APP_VERSION}")' not in text
    assert "Version v.1.192" in text
    assert "KÖR VERSION" not in text
