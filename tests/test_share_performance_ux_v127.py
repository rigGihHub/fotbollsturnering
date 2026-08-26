from pathlib import Path
APP=Path("app.py").read_text(encoding="utf-8")
def test_share_uses_single_popover_without_full_page_toggle_state():
    start=APP.index("# Kompakt delning direkt kopplad till cupheadern")
    end=APP.index('# v143: mobil först',start)
    block=APP[start:end]
    assert 'with st.popover("Dela"' in block
    assert "render_public_share_fragment" not in block
    assert "cn_share_visible_" not in block
def test_share_keeps_qr_and_native_links():
    assert "share_qr = qr_png_bytes(share_url)" in APP
    assert "WhatsApp" in APP and "SMS" in APP and "E-post" in APP
def test_public_match_metrics_merge_played_and_total():
    assert '{len(played_matches)} {html.escape(tr("av"))} {len(published_matches)}' in APP
