from pathlib import Path
APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")
def test_share_uses_native_streamlit_popover():
    assert 'with st.popover("Dela"' in APP
    assert "render_public_share_fragment" not in APP
def test_share_qr_remains_available():
    assert "qr_png_bytes(share_url)" in APP
    assert "Ladda ner QR-kod" in APP
