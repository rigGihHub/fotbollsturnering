from pathlib import Path
APP=Path("app.py").read_text(encoding="utf-8")
def test_public_share_contains_qr_in_popover():
    start=APP.index("def render_public_share_control(")
    end=APP.index('@st.cache_data(show_spinner=False)',start)
    block=APP[start:end]
    assert 'with st.popover("Dela"' in block
    assert "share_qr = qr_png_bytes(share_url)" in block
    assert "qr_col1.image(share_qr" in block
    assert 'tr("Dela länken eller QR-koden till den här cupen.")' in block
def test_qr_download_fallback_remains():
    assert "Ladda ner QR-kod" in APP
