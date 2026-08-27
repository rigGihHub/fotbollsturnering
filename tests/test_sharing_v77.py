
from pathlib import Path

APP=Path("app.py").read_text(encoding="utf-8")


def _public_share_block():
    start=APP.index("# Kompakt delning direkt kopplad till cupheadern")
    end=APP.index("# v143: mobil först",start)
    return APP[start:end]


def test_live_share_controls_support_current_channels():
    block=_public_share_block()
    assert "WhatsApp" in block
    assert "mailto:?subject=" in block
    assert "sms:?&body=" in block
    assert "qr_png_bytes(share_url)" in block


def test_share_links_use_direct_current_cup_url():
    block=_public_share_block()
    assert "share_url = public_cup_url(tournament_id)" in block
    assert "public_slug" in APP


def test_public_view_renders_integrated_share_popover():
    block=_public_share_block()
    assert "cn-share-inline-anchor" in block
    assert 'with st.popover("Dela"' in block
    assert "public_share_toggle_" not in block


def test_legacy_share_panel_code_is_removed():
    assert "cn-share-panel-anchor" not in APP
    assert "def share_panel_html(" not in APP
    assert "def qr_share_panel_html(" not in APP
