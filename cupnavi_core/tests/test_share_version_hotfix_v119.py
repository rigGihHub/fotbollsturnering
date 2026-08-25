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

def test_version_is_hidden_in_public_tournament_view_sidebar():
    text = app_text()
    assert 'if view_mode != "Turneringsvy":\n    st.sidebar.caption(f"CupNavi version {APP_VERSION}")' in text
    assert 'st.sidebar.caption(f"CupNavi version {APP_VERSION}")\nlanguage_options' not in text
