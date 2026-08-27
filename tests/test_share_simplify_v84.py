
from pathlib import Path

APP=Path("app.py").read_text(encoding="utf-8")


def _public_share_block():
    start=APP.index("# Kompakt delning direkt kopplad till cupheadern")
    end=APP.index("# v143: mobil först",start)
    return APP[start:end]


def test_share_uses_one_integrated_popover():
    block=_public_share_block()
    assert 'with st.popover("Dela"' in block
    assert "share_url = public_cup_url(tournament_id)" in block
    assert "share_qr = qr_png_bytes(share_url)" in block


def test_current_share_channels_are_explicit_and_scoped_to_current_cup():
    block=_public_share_block()
    assert "https://wa.me/?text=" in block
    assert "mailto:?subject=" in block
    assert "sms:?&body=" in block
    assert "share_url = public_cup_url(tournament_id)" in block


def test_dead_legacy_share_html_is_removed():
    assert "def share_panel_html(" not in APP
    assert "def render_share_panel(" not in APP
    assert "navigator.share" not in APP
