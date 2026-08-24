from pathlib import Path

def app_text():
    return Path("app.py").read_text(encoding="utf-8")

def test_share_helper_supports_requested_channels():
    text = app_text()
    assert "def share_panel_html(" in text
    assert "navigator.share" in text
    assert "navigator.share" in text
    assert "navigator.share" in text
    assert "navigator.share" in text

def test_share_links_use_direct_current_cup_url():
    text = app_text()
    assert "share_url = public_cup_url(tournament_id)" in text
    assert "SELECT public_slug FROM tournaments WHERE id=?" in text
    assert "public_key" in text

def test_public_view_renders_share_controls():
    text = app_text()
    start = text.index("def render_public_view(")
    public_block = text[start:text.index("init_db()", start)]
    assert "cn-integrated-share" in public_block
    assert "WhatsApp" in public_block
    assert "mailto:?subject=" in public_block
    assert "sms:?&body=" in public_block
    assert "public_share_toggle_" not in public_block

def test_admin_qr_panel_also_has_share_controls():
    text = app_text()
    start = text.index('with st.expander("Dela cupen med QR-kod"')
    block = text[start:start+1200]
    assert 'render_share_panel(tid, tournament["name"])' in block
