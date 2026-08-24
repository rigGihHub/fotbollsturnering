from pathlib import Path


def app_text():
    return Path("app.py").read_text(encoding="utf-8")


def test_fixed_share_is_same_page_details_control():
    text = app_text()
    start = text.index(".cn-fixed-share-button {{position:fixed;")
    block = text[start:start+5000]
    assert "popovertarget=" in block
    assert "class='cn-fixed-share-button'" in block
    assert "popover='auto'" in block
    assert "share=1#cn-share-section" not in block
    assert "target='_blank'" not in block


def test_version_is_hidden_in_public_tournament_view_sidebar():
    text = app_text()
    assert 'if view_mode != "Turneringsvy":\n    st.sidebar.caption(f"CupNavi version {APP_VERSION}")' in text
    assert 'st.sidebar.caption(f"CupNavi version {APP_VERSION}")\nlanguage_options' not in text
