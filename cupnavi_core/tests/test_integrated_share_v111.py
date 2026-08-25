from pathlib import Path


def app_text():
    return Path("app.py").read_text(encoding="utf-8")


def test_public_share_is_single_integrated_inline_panel():
    text = app_text()
    assert "cn_share_visible_" in text
    assert "st.button(" in text
    assert "cn-share-panel-anchor" in text
    assert "public_share_toggle_" not in text
    assert "public_share_open_" not in text
    assert "share=1#cn-share-section" not in text


def test_integrated_share_uses_inline_links_not_public_native_share():
    text = app_text()
    public_start = text.index("def render_public_view(")
    public_block = text[public_start:]
    assert "WhatsApp" in public_block
    assert "mailto:?subject=" in public_block
    assert "sms:?&body=" in public_block
    assert "render_share_panel(tournament_id" not in public_block
    assert "render_qr_share_panel(tournament_id" not in public_block
