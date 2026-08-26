from pathlib import Path
APP=Path("app.py").read_text(encoding="utf-8")
def test_public_share_is_single_integrated_popover():
    assert 'with st.popover("Dela"' in APP
    assert "cn-share-inline-anchor" in APP
    assert "public_share_toggle_" not in APP
    assert "share=1#cn-share-section" not in APP
def test_share_keeps_native_links():
    assert "WhatsApp" in APP
    assert "mailto:?subject=" in APP
    assert "sms:?&body=" in APP
