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
    assert 'f"{PUBLIC_APP_URL}?cup={int(tournament_id)}"' in text

def test_public_view_renders_share_controls():
    text = app_text()
    start = text.index("def render_public_view(")
    public_block = text[start:text.index("init_db()", start)]
    assert 'render_share_panel(tournament_id, tournament["name"])' in public_block
    assert "Messenger" in text
    assert "WhatsApp" in text
    assert "E-post" in text
    assert "SMS" in text

def test_admin_qr_panel_also_has_share_controls():
    text = app_text()
    start = text.index('with st.expander("Dela cupen med QR-kod"')
    block = text[start:start+1200]
    assert 'render_share_panel(tid, tournament["name"])' in block
