from pathlib import Path
APP=Path("app.py").read_text(encoding="utf-8")
OVERVIEW=Path("cupnavi_core/public_match_overview.py").read_text(encoding="utf-8")
def test_share_uses_single_popover_without_full_page_toggle_state():
    start=APP.index("def render_public_share_control(")
    end=APP.index('@st.cache_data(show_spinner=False)',start)
    block=APP[start:end]
    assert 'with st.popover("Dela"' in block
    assert "render_public_share_fragment" not in block
    assert "cn_share_visible_" not in block
def test_share_keeps_qr_and_native_links():
    assert "share_qr = qr_png_bytes(share_url)" in APP
    assert "WhatsApp" in APP and "SMS" in APP and "E-post" in APP
def test_public_match_metrics_merge_played_and_total():
    assert "played_count" in OVERVIEW and "total_matches" in OVERVIEW
    assert "html.escape(tr('av'))" in OVERVIEW
