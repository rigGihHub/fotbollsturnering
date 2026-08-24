from pathlib import Path


def app_text():
    return Path('app.py').read_text(encoding='utf-8')


def test_fixed_share_uses_plain_anchor_label_not_nested_span_markup():
    text = app_text()
    start = text.index(".cn-fixed-share {{position:fixed;")
    block = text[start:start+1800]
    assert "<a class='cn-fixed-share" in block
    assert "📤 {html.escape(tr(\"Dela cupen\"))}</a>" in block
    assert "cn-share-icon" not in block


def test_version_is_hidden_in_public_tournament_view_sidebar():
    text = app_text()
    assert 'if view_mode != "Turneringsvy":\n    st.sidebar.caption(f"CupNavi version {APP_VERSION}")' in text
    assert 'st.sidebar.caption(f"CupNavi version {APP_VERSION}")\nlanguage_options' not in text
